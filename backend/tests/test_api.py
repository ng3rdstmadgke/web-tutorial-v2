from fastapi.testclient import TestClient


class TestLogin:
    """ログイン API のテスト。"""

    def test_login_success(self, client: TestClient):
        """正しい認証情報でログインできる"""
        response = client.post("/api/v1/login", json={"username": "test_admin", "password": "admin_pass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """パスワードが間違っている場合は 401"""
        response = client.post("/api/v1/login", json={"username": "test_admin", "password": "wrong"})
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """存在しないユーザーでログインすると 401"""
        response = client.post("/api/v1/login", json={"username": "nobody", "password": "pass"})
        assert response.status_code == 401


class TestUserCRUD:
    """ユーザー CRUD のテスト。"""

    def test_create_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを作成できる"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "newuser", "password": "secret", "role_ids": [1]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data  # パスワードはレスポンスに含まれない

    def test_create_user_duplicate(self, client: TestClient, auth_headers: dict):
        """既に存在するユーザー名で作成すると 400"""
        client.post(
            "/api/v1/users/",
            json={"username": "duplicate", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        response = client.post(
            "/api/v1/users/",
            json={"username": "duplicate", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_create_user_invalid_role(self, client: TestClient, auth_headers: dict):
        """存在しない role_id を指定すると 400"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "user2", "password": "pass", "role_ids": [999]},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_create_user_validation_error(self, client: TestClient, auth_headers: dict):
        """必須フィールドが欠けると 422"""
        response = client.post(
            "/api/v1/users/",
            json={"password": "pass", "role_ids": [1]},  # username が無い
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_get_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを取得できる"""
        # まず作成
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "getme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        # 取得
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "getme"

    def test_get_user_not_found(self, client: TestClient, auth_headers: dict):
        """存在しないユーザー ID で取得すると 404"""
        response = client.get("/api/v1/users/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_users(self, client: TestClient, auth_headers: dict):
        """ユーザー一覧を取得できる"""
        response = client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # 少なくとも test_admin がいる

    def test_update_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを部分更新できる"""
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "updateme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        response = client.patch(
            f"/api/v1/users/{user_id}",
            json={"avatar_url": "https://example.com/new.png"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["avatar_url"] == "https://example.com/new.png"

    def test_delete_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを削除できる"""
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "deleteme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 204

        # 削除後に取得すると 404
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 404


class TestAuthentication:
    """認証が必要なエンドポイントのテスト。"""

    def test_unauthenticated_access(self, client: TestClient):
        """認証なしでアクセスすると 401"""
        response = client.get("/api/v1/users/")
        assert response.status_code == 401

    def test_invalid_token(self, client: TestClient):
        """無効なトークンで 401"""
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestAuthorization:
    """認可（ロールベース）のテスト。"""

    def test_operator_cannot_create_user(self, client: TestClient, auth_headers: dict):
        """LOCATION_OPERATOR は USER_CREATE 権限がないので 403"""
        # OPERATOR ユーザーを作成
        client.post(
            "/api/v1/users/",
            json={"username": "operator", "password": "pass", "role_ids": [3]},
            headers=auth_headers,
        )
        # OPERATOR でログイン
        login_res = client.post("/api/v1/login", json={"username": "operator", "password": "pass"})
        operator_token = login_res.json()["access_token"]
        operator_headers = {"Authorization": f"Bearer {operator_token}"}

        # ユーザー作成を試みる → 403
        response = client.post(
            "/api/v1/users/",
            json={"username": "forbidden", "password": "pass", "role_ids": [3]},
            headers=operator_headers,
        )
        assert response.status_code == 403


class TestItemCRUD:
    """アイテム CRUD のテスト。"""

    def test_create_and_list_items(self, client: TestClient, auth_headers: dict):
        """アイテムを作成して一覧に含まれることを確認"""
        # 作成
        response = client.post(
            "/api/v1/items/",
            json={"title": "Test Item", "content": "Hello"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        item = response.json()
        assert item["title"] == "Test Item"

        # 一覧
        response = client.get("/api/v1/items/", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert any(i["title"] == "Test Item" for i in items)

    def test_item_ownership(self, client: TestClient, auth_headers: dict):
        """他のユーザーのアイテムにはアクセスできない (403)"""
        # admin でアイテム作成
        create_res = client.post(
            "/api/v1/items/",
            json={"title": "Admin Item", "content": "Secret"},
            headers=auth_headers,
        )
        item_id = create_res.json()["id"]

        # 別ユーザー (OPERATOR) を作成・ログイン
        client.post(
            "/api/v1/users/",
            json={"username": "other_user", "password": "pass", "role_ids": [3]},
            headers=auth_headers,
        )
        login_res = client.post("/api/v1/login", json={"username": "other_user", "password": "pass"})
        other_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # 他人のアイテムを取得 → 403
        response = client.get(f"/api/v1/items/{item_id}", headers=other_headers)
        assert response.status_code == 403
