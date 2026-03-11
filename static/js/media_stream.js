document.addEventListener("DOMContentLoaded", () => {
  const startButton = document.getElementById("start-session");
  const endButton = document.getElementById("end-session");
  const statusIndicator = document.getElementById("status-indicator");
  const videoFeed = document.getElementById("video-feed");
  const donutContainer = document.getElementById("donut-container");
  const centerText = document.getElementById("donut-center-text");
  const templateDetails = document.getElementById("template-details");

  let socket;
  let mediaRecorder;
  let activeStream;
  let selectedTemplate = "";
  let templateData = {};
  let speechEngine; // Added for the Background Council

  const rawTemplates = donutContainer.getAttribute("data-templates");
  
  if (rawTemplates) {
    templateData = JSON.parse(rawTemplates);
    const templateNames = Object.keys(templateData);
    
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("id", "donut-svg");
    svg.setAttribute("viewBox", "0 0 300 300");

    const size = 300;
    const center = size / 2;
    const radius = 110;
    const strokeWidth = 50;
    const total = templateNames.length;
    const gapAngle = total > 1 ? 0.05 : 0;

    if (total === 1) {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", center);
      circle.setAttribute("cy", center);
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", "none");
      circle.setAttribute("class", "donut-slice");
      attachSliceEvent(circle, templateNames[0]);
      svg.appendChild(circle);
    } else {
      const anglePerSlice = (Math.PI * 2) / total;
      templateNames.forEach((templateName, i) => {
        const startAngle = i * anglePerSlice + gapAngle;
        const endAngle = (i + 1) * anglePerSlice - gapAngle;

        const getX = (angle) => center + radius * Math.cos(angle);
        const getY = (angle) => center + radius * Math.sin(angle);

        const startX = getX(startAngle);
        const startY = getY(startAngle);
        const endX = getX(endAngle);
        const endY = getY(endAngle);

        const largeArcFlag = (endAngle - startAngle) > Math.PI ? 1 : 0;
        const d = `M ${startX} ${startY} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endX} ${endY}`;

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d);
        path.setAttribute("fill", "none");
        path.setAttribute("class", "donut-slice");

        attachSliceEvent(path, templateName);
        svg.appendChild(path);
      });
    }
    donutContainer.appendChild(svg);
  }

  function attachSliceEvent(path, templateName) {
    path.addEventListener("mouseenter", () => {
      if (selectedTemplate !== templateName) {
        path.style.stroke = "var(--element-jade)";
      }
      centerText.textContent = templateName;
    });

    path.addEventListener("mouseleave", () => {
      if (selectedTemplate !== templateName) {
        path.style.stroke = "var(--indicator-white)";
      }
      centerText.textContent = selectedTemplate ? selectedTemplate : "SELECT TEMPLATE";
    });

    path.addEventListener("click", () => {
      document.querySelectorAll(".donut-slice").forEach(p => {
        p.classList.remove("selected");
        p.style.stroke = "var(--indicator-white)";
      });
      
      path.classList.add("selected");
      path.style.stroke = "var(--indicator-yellow)";
      
      selectedTemplate = templateName;
      centerText.textContent = templateName;
      centerText.style.borderColor = "var(--element-olive)";
      
      templateDetails.style.display = "block";
      templateDetails.textContent = templateData[templateName];
    });
  }

  startButton.addEventListener("click", async () => {
    try {
      if (!selectedTemplate) {
        statusIndicator.className = "yellow";
        statusIndicator.textContent = "SELECT TEMPLATE FIRST";
        return;
      }
      activeStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      videoFeed.srcObject = activeStream;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/stream?template=${encodeURIComponent(selectedTemplate)}`;
      socket = new WebSocket(wsUrl);

      // Initialize Native Speech Recognition
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        speechEngine = new SpeechRecognition();
        speechEngine.continuous = true;
        speechEngine.interimResults = false; 
        
        speechEngine.onresult = (event) => {
          let finalTranscript = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            }
          }
          if (finalTranscript.trim().length > 0 && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ text: finalTranscript }));
          }
        };
      }

      socket.onopen = () => {
        mediaRecorder = new MediaRecorder(activeStream, { mimeType: "audio/webm" });
        mediaRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
            const buffer = await event.data.arrayBuffer();
            socket.send(buffer);
          }
        };
        mediaRecorder.start(250);
        if (speechEngine) speechEngine.start();

        startButton.disabled = true;
        statusIndicator.className = "green";
        statusIndicator.textContent = `ACTIVE: ${selectedTemplate}`;
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // System 1 Live Audio Response
        if (data.indicator && !data.async_results) {
          statusIndicator.className = data.indicator;
          statusIndicator.textContent = data.message;
        }
        
        // System 2 Async Council & Pacing Response
        if (data.async_results && data.async_results.pacing) {
          if (data.async_results.pacing.indicator !== "green") {
            statusIndicator.className = data.async_results.pacing.indicator;
            statusIndicator.textContent = data.async_results.pacing.message;
          }
        }
      };

      socket.onclose = () => {
        statusIndicator.className = "white";
        statusIndicator.textContent = "SESSION TERMINATED";
        startButton.disabled = false;
        if (speechEngine) speechEngine.stop();
      };

    } catch (error) {
      statusIndicator.className = "pink";
      statusIndicator.textContent = "MEDIA ACCESS DENIED";
    }
  });

  endButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
    if (speechEngine) speechEngine.stop();
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    if (activeStream) {
      activeStream.getTracks().forEach(track => track.stop());
      videoFeed.srcObject = null;
    }
    startButton.disabled = false;
    statusIndicator.className = "white";
    statusIndicator.textContent = "SYSTEM IDLE";
  });
});