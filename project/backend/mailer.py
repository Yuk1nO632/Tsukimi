"""Tencent SES delivery and an explicit development-only local mailbox."""

import json
import os
from pathlib import Path
import threading
from fastapi import HTTPException


class Mailer:
    def __init__(self):
        self.mode = os.getenv("TSUKIMI_MAIL_MODE", "disabled")
        self.region = os.getenv("TSUKIMI_SES_REGION", "ap-hongkong")
        self.sender = os.getenv("TSUKIMI_MAIL_FROM", "")
        self.secret_id = os.getenv("TENCENTCLOUD_SECRET_ID", "")
        self.secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY", "")
        self.templates = {
            purpose: os.getenv(f"TSUKIMI_SES_TEMPLATE_{purpose.upper()}", "")
            for purpose in ("register", "reset")
        }
        self.file = Path(
            os.getenv(
                "TSUKIMI_DEV_MAIL_FILE",
                str(Path(__file__).parent / "data/dev-mail.jsonl"),
            )
        )
        self.lock = threading.Lock()

    @property
    def ready(self):
        if self.mode == "file":
            return os.getenv("TSUKIMI_ENV") == "development"
        return (
            self.mode == "ses"
            and all((self.sender, self.secret_id, self.secret_key))
            and all(
                value.isascii() and value.isdigit() and int(value) > 0
                for value in self.templates.values()
            )
        )

    def send(self, email, purpose, code):
        if not self.ready:
            raise HTTPException(503, "邮件服务尚未配置，请按账号指南完成后端邮件设置。")
        if self.mode == "file":
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.lock, self.file.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {"email": email, "purpose": purpose, "code": code},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            return
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ses.v20201002 import ses_client, models

        profile = ClientProfile(httpProfile=HttpProfile(reqTimeout=12))
        client = ses_client.SesClient(
            credential.Credential(self.secret_id, self.secret_key), self.region, profile
        )
        payload = models.SendEmailRequest()
        payload.from_json_string(
            json.dumps(
                {
                    "FromEmailAddress": self.sender,
                    "Destination": [email],
                    "Subject": (
                        "Tsukimi 注册验证"
                        if purpose == "register"
                        else "Tsukimi 密码重置"
                    ),
                    "Template": {
                        "TemplateID": int(self.templates[purpose]),
                        "TemplateData": json.dumps({"code": code, "minutes": "5"}),
                    },
                    "TriggerType": 1,
                }
            )
        )
        try:
            client.SendEmail(payload)
        except TencentCloudSDKException:
            raise HTTPException(503, "邮件暂时无法发送，请稍后重试。") from None
