from locust import HttpUser, task, between
import random

class MyAppUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def monitor(self):
        self.client.get("/monitor")

    @task(1)
    def advice(self):
        self.client.get("/advice")

    @task(1)
    def ai_chat(self):
        # 模拟 POST 聊天（需构造 JSON）
        payload = {"prompt": "Hello", "session_id": "test"}
        self.client.post("/api/chat", json=payload)
