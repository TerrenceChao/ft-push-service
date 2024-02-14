from typing import Any, Dict
import asyncio
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


class DataService:

    '''
    TODO: 
    1. 先緩存在 local memory, 
    因為 message queue 採用"至多消費一次"模式,
    所以不會有重複的通知; 
    當然還是要考慮到"重複通知"的情況
    2. 將 local memory 的資料 "定期" 寫入 DB
    3. local memory "超過一定數量" 時, 也要寫入 DB
    '''

    async def batch_write_items(self, item: Any):
        log.info(f'\n\nbatch write item: {item}\n\n')
        await asyncio.sleep(5)
        
        # 如果 local memory 超過一定數量, 就寫入 DB
        await self.flush()

    def get_history_msgs(self, role_id: int, role: str):
        return [
            {
                'title': 'Teacher Eva apply for a job',
                'content': {
                    'role_id': f'company id: {role_id}',
                    'jid': 'job id: 123',
                    'tid': 'teacher id',
                    'rid': 'resume id: 456',
                    'title': 'Job Title',
                },
                'category': 'notification',
                'read': False,
            },
            {
                'title': 'Teacher Gary apply for a job',
                'content': {
                    'role_id': f'company id: {role_id}',
                    'jid': 'job id: 234',
                    'tid': 'teacher id 2',
                    'rid': 'resume id: 567',
                    'title': 'Job Title 22',
                },
                'category': 'notification',
                'read': True,
            },
            {
                'title': 'Teacher John apply for a job',
                'content': {
                    'role_id': f'company id: {role_id}',
                    'jid': 'job id: 678',
                    'tid': 'teacher id 3',
                    'rid': 'resume id: 789',
                    'title': 'Job Title 333',
                },
                'category': 'notification',
                'read': False,
            }
        ]
    
    def msg_read(self, role_id: int, role: str, data: Dict):
        log.info(f'role_id: {role_id}, msg read: True, data: {data}')

    '''
    TODO: 當 Lambda 被關閉時，將 local memory 的資料寫入 DB
    '''
    async def flush(self):
        log.info('\n\n\n 將 local memory 的資料寫入 DB \n\n\n')


_data_service = DataService()
