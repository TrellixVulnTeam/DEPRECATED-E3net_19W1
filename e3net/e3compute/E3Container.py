#! /usr/bin/python3
from e3net.e3compute.DBCompute import *
from e3net.e3compute.E3COMPUTEHost import * 
from uuid import uuid4
import json
from datetime import datetime
from e3net.e3common.E3LOG import get_e3loger
from e3net.e3common.E3MQ import E3MQClient

e3log=get_e3loger('e3compute')
mq_scheduler=E3MQClient(queue_name='e3-scheduler-mq',
                        user='e3net',
                        passwd='e3credentials')

class Container(E3COMPUTEDBBase):
    __tablename__='container'
    
    id=Column(String(64),primary_key=True)
    name=Column(String(64),nullable=True)
    description=Column(Text,nullable=True)
    created_at=Column(DateTime(),nullable=False,default=datetime.now)
    image_id=Column(String(64),ForeignKey('image.id'))
    flavor_id=Column(String(64),ForeignKey('flavor.id'))
    host=Column(String(64),nullable=True) #the chosen host to accommodate target container

    container_status=Column(Enum('unknown','running','stopped'),nullable=False,default='unknown')
    task_status=Column(Enum('created','spawning','deployed','failed'),nullable=False,default='created')

    tenant_id=Column(String(64),nullable=False) # not constrained to tenant.id since it resides in other table
    def __repr__(self):
        obj=dict()
        obj['id']=self.id
        obj['name']=self.name
        obj['description']=self.description
        obj['image_id']=self.image_id
        obj['flavor_id']=self.flavor_id
        obj['host']=self.host
        obj['container_status']=self.container_status
        obj['task_status']=self.task_status
        obj['tenant_id']=self.tenant_id
        obj['created_at']=self.created_at.ctime()
        return str(obj)

def set_e3container_status(id,status):
    session=E3COMPUTEDBSession()
    try:
        session.begin()
        container=session.query(Container).filter(Container.id==id).first()
        if not container:
            return False
        container.task_status=status
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()

def register_e3container(tenant_id,name,image_id,flavor_id,desc=''):
    session=E3COMPUTEDBSession()
    try:
        session.begin()
        container=Container()
        container.id=str(uuid4())
        container.name=name
        container.description=desc
        container.image_id=image_id
        container.flavor_id=flavor_id
        container.container_status='unknown'
        container.task_status='created'
        container.tenant_id=tenant_id
        session.add(container)
        session.commit()
        # notify scheduler to find a host and network area to boot the container
        msg=dict()
        msg['action']='boot'
        msg['container_id']=container.id
        msg=json.dumps(msg)
        enqueue_rc=mq_scheduler.enqueue_message(str(msg))
        if not enqueue_rc:
            e3log.error('sending message:%s to scheduler fails'%(str(msg)))
            set_e3container_status(container.id,'failed')
        else:
            e3log.info('sending message:%s to scheduler succeeds'%(str(msg)))
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()
def get_e3container_by_id(id):
    session=E3COMPUTEDBSession()
    container=None
    try:
        session.begin()
        container=session.query(Container).filter(Container.id==id).first()
    except:
        container=None
    finally:
        session.close()
    return container
def get_e3containers(tenant_id=None):
    session=E3COMPUTEDBSession()
    lst=list()
    try:
        session.begin()
        if tenant_id :
            lst=session.query(Container).filter(Container.tenant_id==tenant_id).all()
        else:
            lst=session.query(Container).all()
    except:
        lst=list()
    finally:
        session.close()
    return lst
def unregister_e3container_pre(container_id):
    session=E3COMPUTEDBSession()
    try:
        session.begin()
        container=session.query(Container).filter(Container.id==container_id).first()
        if not container:
            return False
        #notify scheduler to delete container no matter what state the container is in
        print('delete container:',container)
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()
def unregister_e3container_post(container_id):
    session=E3COMPUTEDBSession()
    try:
        session.begin()
        container=session.query(Container).filter(Container.id==container_id).first()
        if not container:
            return False
        session.delete(container)
        session.commit()
        #this function will destroy entry in database
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()
    
if __name__=='__main__':
    init_e3compute_database('mysql+pymysql://e3net:e3credientials@localhost/E3compute',True)
    create_e3compute_database_entries()
    #print(unregister_e3container_post('098d5d4d-c296-449e-9771-d964b8355bff'))
    

    #print(get_e3container_by_id('33629f72-789d-4749-ba6b-60e427bf2316'))
    #print(get_e3containers())
 
    print(register_e3container('2c90d294-34b0-43bd-8c95-d716f87f829f',
                        'vrouter1',
                        image_id='936e3279-870a-492b-807e-6196b241c181',
                        flavor_id='ff9d853e-2376-4915-8525-6aa2e3df7d6f',
                        desc='a virtual router prototype'))
