import * as React from "react"

const MOBILE_BREAKPOINT = 768

// メディアクエリの変化を購読する（変化時に callback を呼び、解除関数を返す）
function subscribe(callback: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener("change", callback)
  return () => mql.removeEventListener("change", callback)
}

export function useIsMobile() {
  return React.useSyncExternalStore(
    subscribe,
    () => window.innerWidth < MOBILE_BREAKPOINT,  // クライアントでの現在値
    () => false,                                  // 初期値を返す関数。SSR とハイドレーション最初の描画で評価される 
  )
}