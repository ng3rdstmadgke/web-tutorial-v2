import { defineConfig, devices } from "@playwright/test";

// devcontainer から見たアプリの入口は nginx (proxy サービス、コンテナ内ポート 8080)。
// 環境変数で上書き可能にしておく。
const baseURL = process.env.E2E_BASE_URL ?? "http://proxy:8080";

// TestConfig: https://playwright.dev/docs/api/class-testconfig
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,  // テストファイルを並列実行(単一ファイル内のテストは順番に実行)
  // レポーター: ターミナルに list 出力 + HTML レポート(playwright-report/)も生成。
  // open:"never" は実行後に自動でブラウザを開かない設定（devcontainer 向け。show-report で開く）
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure", // 失敗したテストのトレースを残す（デバッグ用）
  },
  projects: [
    // 1) ログインして storageState を保存する setup プロジェクト
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/  // このパターンにマッチするファイルが実行される
      // use を指定していないので既定のブラウザ(chromium)で動く。
      // ログインして Cookie を保存するだけなのでエンジンは問わない
    },
    // 2) 本体テスト。setup が保存した認証状態を使い回す
    {
      name: "chromium",
      use: {  // オプション設定
        ...devices["Desktop Chrome"],  // 利用するブラウザの設定: https://github.com/microsoft/playwright/blob/main/packages/playwright-core/src/server/deviceDescriptorsSource.json
        storageState: "playwright/.auth/user.json",  // setupで取得した認証情報が保存されているファイルを指定
      },
      dependencies: ["setup"],  // setupの後に実行される
    },
  ],
});