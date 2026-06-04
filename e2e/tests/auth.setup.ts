import { test as setup } from "@playwright/test";

const authFile = "playwright/.auth/user.json";

// 一度だけ UI ログインし、Cookie を含む storageState を保存する。
// 以降の本体テストはこの状態を読み込んでログイン済みで始まる。
setup("authenticate", async ({ page }) => {
  await page.goto("/login");

  // 入力欄は getByLabel が推奨
  await page.getByLabel("ユーザー名").fill("sys_admin");
  await page.getByLabel("パスワード").fill("admin");
  await page.getByRole("button", { name: "ログイン" }).click();

  // ログイン成功後、トップ(/)は /items へリダイレクトされる
  await page.waitForURL("**/items");

  // Cookieの情報をファイルに書き出す
  await page.context().storageState({ path: authFile });
});