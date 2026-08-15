import hashlib
import base64
import time
import random
from urllib.parse import urlencode


class MaoyanSigner:
    """猫眼签名生成器"""
    
    FIXED_KEY = 'A013F70DB97834C0A5492378BD76C53A'
    CHANNEL_ID = 40011
    S_VERSION = 2
    
    @classmethod
    def generate_sign(cls, method='GET', user_agent=None):
        """生成签名和参数"""
        timestamp = str(int(time.time() * 1000))
        index = str(random.randint(1, 1000))
        
        if not user_agent:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        UA_base64 = base64.b64encode(user_agent.encode('utf-8')).decode('utf-8')
        
        sign_params = [
            ("method", method),
            ("timeStamp", timestamp),
            ("User-Agent", UA_base64),
            ("index", index),
            ("channelId", str(cls.CHANNEL_ID)),
            ("sVersion", str(cls.S_VERSION)),
            ("key", cls.FIXED_KEY)
        ]
        
        raw_str = "&".join([f"{k}={v}" for k, v in sign_params])
        clean_str = " ".join(raw_str.split())
        signKey = hashlib.md5(clean_str.encode('utf-8')).hexdigest()
        
        return {
            'timeStamp': timestamp,
            'index': index,
            'signKey': signKey,
            'channelId': cls.CHANNEL_ID,
            'sVersion': cls.S_VERSION,
            'UA_base64': UA_base64
        }
    
    @classmethod
    def build_url(cls, base_url, **kwargs):
        """构建带签名的URL"""
        sign_params = cls.generate_sign()
        query_params = {
            'timeStamp': sign_params['timeStamp'],
            'index': sign_params['index'],
            'signKey': sign_params['signKey'],
            'channelId': sign_params['channelId'],
            'sVersion': sign_params['sVersion'],
            **kwargs  # 其他参数
        }
        return f"{base_url}?{urlencode(query_params)}"