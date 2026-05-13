"use client";

import { useState } from "react";

export function Counter() {
  const [count, setCount] = useState(0);
  return (
    <div className="flex items-center gap-4">
      <button
        onClick={() => setCount(count + 1)}
        className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
      >
        +1
      </button>
      <span>count: {count}</span>
    </div>
  );
}