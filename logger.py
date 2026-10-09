from datetime import datetime
from pathlib import Path
from typing import Literal

levels = Literal["WARN", "INFO", "ERROR", "SUCCESS"]

class Logger():
    
    def __init__(self) -> None:
        self._app_name = 'Framex'
        #self._levels = ("WARN", "INFO", "ERROR", "SUCCESS")
        self._APP_LOG_DIR = Path(Path.home(), "Desktop")
        
        

    @property
    def APP_LOG_DIR(self):
        return self._APP_LOG_DIR  
    
    @property
    def app_name(self):
        return self._app_name.upper()
    
    def __getCurrentTime(self) -> datetime:
        return datetime.now()
    
    def __writeToLogFile(self, content:str):
        
        
        path_logs = Path(self.APP_LOG_DIR, self.app_name, 'logs')
        file_log = Path(path_logs, "logs.txt")
        
        if path_logs.exists() != True:
            path_logs.mkdir(parents=True, exist_ok=True)
            
        if file_log.exists() != True:
            file_log.touch()
            
        with open(file_log, 'a') as f:
            f.write(f'{content}\n')
            
        
    def log(self, message:str, level:levels):
        content = f'[{self.app_name}] - {self.__getCurrentTime()} - {level}: {message}'
        self.__writeToLogFile(content)
        return content
    
    