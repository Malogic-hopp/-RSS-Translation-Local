import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from .base import BaseTranslator

class TencentTranslator(BaseTranslator):
    def __init__(self, secret_id, secret_key, source_lang="auto", target_lang="zh", region="ap-shanghai"):
        super().__init__(source_lang, target_lang)
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        
        # Initialize Tencent Client
        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            httpProfile = HttpProfile()
            httpProfile.endpoint = "tmt.tencentcloudapi.com"
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            self.client = tmt_client.TmtClient(cred, self.region, clientProfile)
        except Exception as e:
            print(f"Error initializing Tencent Client: {e}")
            self.client = None

    def translate(self, content):
        if not content or not self.client:
            return content

        try:
            req = models.TextTranslateRequest()
            
            # Map languages if necessary
            # Tencent uses 'zh' for Simplified Chinese, 'auto' for auto.
            # Ensure target_lang is correct for Tencent
            t_lang = self.target_lang
            if t_lang.lower() in ['zh-cn', 'zh_cn']:
                t_lang = 'zh'
            
            params = {
                "SourceText": content,
                "Source": self.source_lang,
                "Target": t_lang,
                "ProjectId": 0
            }
            req.from_json_string(json.dumps(params))

            resp = self.client.TextTranslate(req)
            # The response is a JSON string, we need to parse it or use the object properties
            # The SDK returns an object, but we can dump it to check or just access properties.
            # resp.TargetText is what we want.
            
            return resp.TargetText

        except TencentCloudSDKException as err:
            print(f" [Tencent API Error: {err}]")
            return None
        except Exception as e:
            print(f" [Tencent Translation Error: {e}]")
            return None
