from sqlalchemy import select, update, desc, delete, asc
from sqlalchemy.ext.asyncio import AsyncSession
from models.activity_log import ActivityLog
from utils import logger


async def db_create_activity_log(db: AsyncSession,
                                 user_id: int,
                                 action: str,
                                 resource_type: str,
                                 resource_id: str,
                                 resource_name: str,
                                 details: str,
                                 ip_address: str,
                                 user_agent: str,
                                 ):
    log = ActivityLog(user_id=user_id,
                      action=action,
                      resource_type=resource_type,
                      resource_id=resource_id,
                      resource_name=resource_name,
                      details=details,
                      ip_address=ip_address,
                      user_agent=user_agent)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    logger.info(f"[USER_ACTIVITY] action={action} user_id={user_id} resource_type={resource_type} resource_id={resource_id} \
                resource_name={resource_name} details={details} ip={ip_address} user_agent={user_agent}")
    return log
