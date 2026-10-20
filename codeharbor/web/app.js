(() => {
  "use strict";

  const status = document.getElementById("connection-status");
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    status.textContent = "已连接";
  });
  socket.addEventListener("close", () => {
    status.textContent = "连接已断开";
  });
  socket.addEventListener("error", () => {
    status.textContent = "连接失败";
  });
})();
