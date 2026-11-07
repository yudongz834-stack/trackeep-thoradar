// ============================================================
// ThorRadar · AI 接口 CORS 透传 Worker（无状态·不存储任何数据）
// ============================================================
// 用途：部分 AI 服务商禁止网页直接调用（浏览器跨域限制）。
//       本 Worker 部署在你自己的 Cloudflare 账号上（免费额度足够），
//       作用＝把雷达发出的请求原样转发给你的 AI 服务商。
//       你的 API Key 依然只存在你自己的浏览器里，Worker 全程
//       转发、不落盘、不记录。
//
// 部署三步（约 5 分钟）：
//   1. dash.cloudflare.com → Workers & Pages → Create Worker
//   2. 把本文件全部内容粘贴进去，只改下面一行 TARGET
//   3. Deploy → 复制给你的地址（https://你起的名.你的子域.workers.dev）
//      → 在雷达设置的「接口地址 BaseURL」里填这个地址
//
// 安全说明：
//   - Worker 不存储任何 Key 与请求内容（纯透传，无 KV/存储绑定）
//   - 建议在 AI 服务商后台生成「限额＋可随时吊销」的专用 Key
//   - 公共电脑不要填写任何 Key
// ============================================================

// 改这里：你的 AI 服务商接口根地址（以 /v1 或 /anthropic 结尾，按服务商文档）
const TARGET = "https://your-ai-endpoint.example.com/anthropic";

export default {
  async fetch(request, env) {
    // 支持环境变量覆盖（可选）：Workers 设置里配 TARGET 变量则优先
    const base = (env && env.TARGET) || TARGET;

    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }));
    }
    if (request.method !== "POST") {
      return withCors(new Response("POST only", { status: 405 }));
    }

    const url = new URL(request.url);
    // 路径原样拼接：客户端 BaseURL 填 Worker 地址，路径部分由雷达自动补
    const upstream = base.replace(/\/+$/, "") + url.pathname + url.search;

    const headers = new Headers(request.headers);
    headers.delete("host");                 // 换目标，主机头必须换掉
    headers.delete("origin");
    headers.delete("referer");
    headers.delete("cookie");               // Cookie 不透传（无需也不该带）

    const resp = await fetch(upstream, {
      method: "POST",
      headers,
      body: request.body,
    });
    return withCors(new Response(resp.body, resp));
  },
};

function withCors(resp) {
  resp.headers.set("Access-Control-Allow-Origin", "*");
  resp.headers.set("Access-Control-Allow-Headers", "*");
  resp.headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  resp.headers.set("Access-Control-Max-Age", "86400");
  return resp;
}
