"""ส่วนกลางของสคริปต์สาธิต: อ่านอาร์กิวเมนต์ร่วมและ login เอา access token"""

import argparse
import os

import httpx


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8000/api/v1"),
        help="เช่น https://campus-api-xxxx.asia-southeast1.run.app/api/v1",
    )
    parser.add_argument("--email", default=os.getenv("DEMO_EMAIL", "student1@smartcampus.dev"))
    parser.add_argument("--password", default=os.getenv("DEMO_PASSWORD", "student12345"))
    return parser


async def login(client: httpx.AsyncClient, email: str, password: str) -> dict[str, str]:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
