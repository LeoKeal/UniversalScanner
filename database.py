import sqlite3
import json
from datetime import datetime
import requests

class DatabaseManager:
    def __init__(self, server_url=None):
        self.server_url = server_url
        self.local_db = 'scanner_data.db'
        self.init_local_db()
    
    def init_local_db(self):
        """初始化本地SQLite数据库"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,
                barcode_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                synced INTEGER DEFAULT 0,
                sync_timestamp DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_scan_record(self, barcode, barcode_type="UNKNOWN"):
        """保存扫描记录"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scan_records (barcode, barcode_type, timestamp)
            VALUES (?, ?, ?)
        ''', (barcode, barcode_type, datetime.now()))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_unsynced_records(self):
        """获取未同步的记录"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scan_records WHERE synced = 0 ORDER BY timestamp
        ''')
        
        records = cursor.fetchall()
        conn.close()
        
        return records
    
    def mark_as_synced(self, record_id):
        """标记记录为已同步"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE scan_records 
            SET synced = 1, sync_timestamp = ?
            WHERE id = ?
        ''', (datetime.now(), record_id))
        
        conn.commit()
        conn.close()
    
    def sync_to_server(self):
        """同步数据到服务器"""
        if not self.server_url:
            return False, "未配置服务器地址"
        
        unsynced = self.get_unsynced_records()
        success_count = 0
        
        for record in unsynced:
            record_id, barcode, barcode_type, timestamp, synced, sync_timestamp = record
            
            data = {
                'barcode': barcode,
                'type': barcode_type,
                'timestamp': timestamp
            }
            
            try:
                response = requests.post(
                    f"{self.server_url}/api/scan",
                    json=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.mark_as_synced(record_id)
                    success_count += 1
            except:
                continue
        
        return True, f"成功同步 {success_count}/{len(unsynced)} 条记录"