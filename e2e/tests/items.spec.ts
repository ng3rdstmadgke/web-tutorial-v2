import { test, expect } from "@playwright/test";

test("ログイン済みでアイテム管理画面が表示される", async ({ page }) => {
  await page.goto("/items");
  await expect(
    page.getByRole("heading", { name: "アイテム管理" }),
  ).toBeVisible();
});

test("アイテムを作成・編集・削除できる", async ({ page }) => {
  // 他のテスト/データと衝突しないよう一意なタイトルにする
  const title = `E2E item ${Date.now()}`;
  const updatedContent = "updated content";

  await page.goto("/items");

  // --- 作成 ---
  await page.getByRole("button", { name: "新規作成" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("タイトル").fill(title);
  await dialog.getByLabel("内容").fill("hello");
  await dialog.getByRole("button", { name: "保存" }).click();

  // 一覧に作成した行が出る
  const row = page.getByRole("row", { name: new RegExp(title) });
  await expect(row).toBeVisible();
  await expect(row).toContainText("hello");

  // --- 編集 ---
  await row.getByRole("button", { name: "編集" }).click();
  const editDialog = page.getByRole("dialog");
  await editDialog.getByLabel("内容").fill(updatedContent);
  await editDialog.getByRole("button", { name: "保存" }).click();
  await expect(row).toContainText(updatedContent);

  // --- 削除（楽観的更新で即座に消える）---
  await row.getByRole("button", { name: "削除" }).click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "削除" })
    .click();
  await expect(
    page.getByRole("row", { name: new RegExp(title) }),
  ).toHaveCount(0);
});