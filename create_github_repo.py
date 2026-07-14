#!/usr/bin/env python3
"""
创建 GitHub 仓库并推送代码
需要 GitHub Personal Access Token (classic)
"""

import requests
import sys
import os

REPO_DIR = r"C:\Users\tnetstar qjm\.qclaw\workspace\sip_direct_kivy"
GITHUB_API = "https://api.github.com"

def main():
    # 获取 token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token = input("请输入 GitHub Personal Access Token: ").strip()
    
    if not token:
        print("错误: 需要 GitHub Token")
        sys.exit(1)
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # 获取用户信息
    print("正在验证 token...")
    resp = requests.get(f"{GITHUB_API}/user", headers=headers)
    if resp.status_code != 200:
        print(f"错误: Token 无效 ({resp.status_code})")
        sys.exit(1)
    
    user = resp.json()
    username = user["login"]
    print(f"✓ 已验证用户: {username}")
    
    # 创建仓库
    print("\n正在创建 GitHub 仓库...")
    repo_data = {
        "name": "sipphone",
        "description": "SIP Phone for Android - Kivy based VoIP client for 国贸游泳馆值班呼叫系统",
        "private": False,
        "has_wiki": False,
        "auto_init": False
    }
    
    resp = requests.post(f"{GITHUB_API}/user/repos", headers=headers, json=repo_data)
    
    if resp.status_code == 201:
        repo = resp.json()
        repo_url = repo["html_url"]
        clone_url = repo["clone_url"]
        print(f"✓ 仓库已创建: {repo_url}")
    elif resp.status_code == 422:
        # 仓库可能已存在
        print("仓库 sipphone 已存在，正在获取...")
        resp = requests.get(f"{GITHUB_API}/repos/{username}/sipphone", headers=headers)
        if resp.status_code == 200:
            repo = resp.json()
            repo_url = repo["html_url"]
            clone_url = repo["clone_url"]
            print(f"✓ 已找到仓库: {repo_url}")
        else:
            print(f"错误: 无法访问仓库 ({resp.status_code})")
            sys.exit(1)
    else:
        print(f"错误: 创建仓库失败 ({resp.status_code})")
        print(resp.text)
        sys.exit(1)
    
    # 添加 remote 并推送
    print(f"\n正在推送代码到 {clone_url}...")
    
    import subprocess
    
    # 添加 remote
    subprocess.run(["git", "-C", REPO_DIR, "remote", "remove", "origin"], capture_output=True)
    subprocess.run(["git", "-C", REPO_DIR, "remote", "add", "origin", clone_url], check=True)
    
    # 推送
    result = subprocess.run(
        ["git", "-C", REPO_DIR, "push", "-u", "origin", "master"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ 代码已推送!")
        print(f"\n🎉 完成!")
        print(f"   仓库地址: {repo_url}")
        print(f"   Actions: {repo_url}/actions")
        print(f"\n构建 APK:")
        print(f"   1. 访问 {repo_url}/actions")
        print(f"   2. 点击 'Build Android APK'")
        print(f"   3. 点击 'Run workflow'")
        print(f"   4. 下载 'sipphone-debug' artifact")
    else:
        print(f"错误: 推送失败")
        print(result.stderr)

if __name__ == "__main__":
    main()
