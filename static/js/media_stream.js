const startButton = document.getElementById("start-session");
const statusIndicator = document.getElementById("status-indicator");
const videoFeed = document.getElementById("video-feed");

let socket;
let mediaRecorder;

startButton.addEventListener("click", async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true
    });
    
    videoFeed.srcObject = stream;
    
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/stream`;
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          const buffer = await event.data.arrayBuffer();
          socket.send(buffer);
        }
      };
      
      mediaRecorder.start(250);
      startButton.textContent = "Session Active";
      startButton.disabled = true;
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.indicator) {
        statusIndicator.className = data.indicator;
        statusIndicator.textContent = data.message;
      }
    };

  } catch (error) {
    statusIndicator.className = "pink";
    statusIndicator.textContent = "Media Access Denied";
  }
});