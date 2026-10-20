from aiogram.fsm.state import State, StatesGroup


class DocumentUploadState(StatesGroup):
    waiting_for_real_name = State()       
    waiting_for_location = State()        
    waiting_for_version_action = State()  
