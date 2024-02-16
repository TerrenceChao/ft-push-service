from pydantic import BaseModel


class UserDTO(BaseModel):
    role: str
    role_id: int
    
    def user_id(self):
        return f'{self.role}:{self.role_id}'
