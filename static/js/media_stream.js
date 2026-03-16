// static/js/media_stream.js
import { startAudioCapture, stopAudioCapture } from './audio_processor.js';

document.addEventListener("DOMContentLoaded", () => {
  const sessionToggle = document.getElementById("session-toggle");
  const statusIndicator = document.getElementById("status-indicator");
  const videoFeed = document.getElementById("video-feed");
  const donutContainer = document.getElementById("donut-container");
  const centerText = document.getElementById("donut-center-text");
  const templateDetails = document.getElementById("template-details");
  
  const idlePanel = document.getElementById("idle-panel");
  const activeSessionPanel = document.getElementById("active-session-panel");
  const eventLog = document.getElementById("live-event-log");

  let socket;
  let activeStream;
  let selectedTemplate = "";
  let templateData = window.TEMPLATE_DATA || {};
  let isSessionActive = false;

  // Auto-Recorder Variables
  let mediaRecorder = null;
  let recordedChunks = [];

  // Globally expose hover interaction functions for SVG inline handlers
  window.hoverRingItem = function(selectedId, categoryLabel) {
    const slice = document.getElementById('slice-' + selectedId);
    if (slice) {
        slice.classList.add("hover");
    }
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = categoryLabel;
    }
  };

  window.resetRingItem = function(selectedId) {
    const slice = document.getElementById('slice-' + selectedId);
    if (slice) {
        slice.classList.remove("hover");
    }
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = selectedTemplate ? selectedTemplate : "SELECT ARCHETYPE";
    }
  };

  window.clickRingItem = function(selectedId, categoryLabel) {
    document.querySelectorAll(".donut-slice").forEach(p => {
        p.classList.remove("selected", "hover");
    });
    
    const activeSlice = document.getElementById('slice-' + selectedId);
    if (activeSlice) {
        activeSlice.classList.add("selected");
    }
    
    selectedTemplate = categoryLabel;
    
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = categoryLabel;
        centerNode.style.borderColor = "var(--element-jade)";
    }
    
    const detailsNode = document.getElementById("template-details");
    if (detailsNode) {
        detailsNode.style.display = "block";
        detailsNode.textContent = templateData[categoryLabel]?.description || "Archetype configuration initialized.";
    }
  };

  function logEvent(message) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const entry = document.createElement("div");
    entry.style.marginBottom = "4px";
    entry.innerHTML = `<span style="color: var(--element-olive); font-weight: bold;">[${time}]</span> ${message}`;
    eventLog.appendChild(entry);
    eventLog.scrollTop = eventLog.scrollHeight; 
  }

  let playbackContext;
  let nextPlaybackTime = 0;
  let activeAudioNodes = [];

  window.isCharonSpeaking = false;
  window.lastAgentSpeechTime = 0; 
  window.charonSpeakingTimeout = null; 

  window.stopAgentAudio = function() {
    activeAudioNodes.forEach(source => {
        try { source.stop(); } catch(e) {}
    });
    activeAudioNodes = [];
    if (window.charonSpeakingTimeout) {
        clearTimeout(window.charonSpeakingTimeout);
        window.charonSpeakingTimeout = null;
    }
    window.isCharonSpeaking = false;
    window.lastAgentSpeechTime = Date.now(); 
    if (playbackContext) {
        nextPlaybackTime = playbackContext.currentTime;
    }
  };

  async function startSession() {
    try {
      if (!selectedTemplate) {
        statusIndicator.className = "orange";
        statusIndicator.textContent = "SELECT ARCHETYPE TO BEGIN";
        return;
      }

      isSessionActive = true;
      sessionToggle.textContent = "TERMINATE SESSION";
      idlePanel.style.display = "none";
      activeSessionPanel.style.display = "flex";
      eventLog.innerHTML = ""; 
      logEvent(`System Alignment: Loading ${selectedTemplate} Protocol...`);

      const requiresVideo = templateData[selectedTemplate]?.requires_video_audit || false;
      const requiresScreen = selectedTemplate === "Demo Video" || templateData[selectedTemplate]?.requires_screen_audit || false;
      
      let audioConstraints = { echoCancellation: true, noiseSuppression: true, autoGainControl: true };

      if (requiresScreen) {
          logEvent("Screen Modality requested. Establishing display link...");
          const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
          const micStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
          
          activeStream = new MediaStream([
              ...screenStream.getVideoTracks(),
              ...micStream.getAudioTracks()
          ]);

          screenStream.getVideoTracks()[0].onended = () => {
              logEvent("Display link severed by user.");
              if (isSessionActive) terminateSessionUI();
          };
      } else {
          activeStream = await navigator.mediaDevices.getUserMedia({ 
              video: requiresVideo, 
              audio: audioConstraints 
          });
      }

      videoFeed.srcObject = activeStream;
      videoFeed.play();
      
      logEvent(`Sensors Engaged: Visual Auditing is ${requiresVideo || requiresScreen ? "ACTIVE" : "OFFLINE"}`);

      // Auto-Play Fix: Resume and initialize hardware on button click
      window.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      playbackContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      await window.audioCtx.resume();
      await playbackContext.resume();

      // Inject Unified Auto-Recorder for Demo Video
      if (selectedTemplate === "Demo Video") {
          recordedChunks = [];
          try {
              // Matrix Mixer: Mix Mic and Agent Voice for the recording stream
              window.recordingDestination = window.audioCtx.createMediaStreamDestination();
              const micSource = window.audioCtx.createMediaStreamSource(activeStream);
              micSource.connect(window.recordingDestination);

              const combinedStream = new MediaStream([
                  ...activeStream.getVideoTracks(),
                  ...window.recordingDestination.stream.getAudioTracks()
              ]);

              mediaRecorder = new MediaRecorder(combinedStream, { mimeType: 'video/webm; codecs=vp9' });
              mediaRecorder.ondataavailable = function(e) {
                  if (e.data.size > 0) {
                      recordedChunks.push(e.data);
                  }
              };
              mediaRecorder.onstop = function() {
                  const blob = new Blob(recordedChunks, { type: 'video/webm' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.style.display = 'none';
                  a.href = url;
                  a.download = `Auditore_Demo_Video_${new Date().getTime()}.webm`;
                  document.body.appendChild(a);
                  a.click();
                  setTimeout(() => {
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                  }, 100);
              };
              mediaRecorder.start();
              logEvent("Auto-Recording Active Matrix: Combined system/agent audio link established.");
          } catch (err) {
              logEvent("Warning: MediaRecorder initialization failed.");
          }
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/stream?template=${encodeURIComponent(selectedTemplate)}`;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        logEvent("Secure matrix link established.");
        
        try {
          startAudioCapture(socket, activeStream);

          const analyser = window.audioCtx.createAnalyser();
          const micSource = window.audioCtx.createMediaStreamSource(activeStream);
          micSource.connect(analyser);
          analyser.fftSize = 256;
          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          window.vadInterval = setInterval(() => {
              // Ironclad 1000ms suppression barrier
              if (window.isCharonSpeaking || (Date.now() - window.lastAgentSpeechTime < 1000)) return; 

              analyser.getByteFrequencyData(dataArray);
              let sum = 0;
              for(let i = 0; i < dataArray.length; i++) sum += dataArray[i];
              let avg = sum / dataArray.length;
              
              if (avg > 38 && selectedTemplate !== "Demo Video") { 
                  logEvent("Barge-in detected. Recalibrating agent dialogue...");
                  window.stopAgentAudio();
                  window.lastAgentSpeechTime = Date.now(); // Reset barrier
                  if (socket.readyState === WebSocket.OPEN) {
                      socket.send(JSON.stringify({ "client_event": "barge_in" }));
                  }
              }
          }, 50);

          if (requiresVideo || requiresScreen) {
              const canvas = document.createElement("canvas");
              const ctx = canvas.getContext("2d");
              
              window.videoAuditInterval = setInterval(() => {
                  if (socket.readyState === WebSocket.OPEN && videoFeed.readyState === videoFeed.HAVE_ENOUGH_DATA) {
                      canvas.width = 640;
                      canvas.height = 480;
                      ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
                      const base64Frame = canvas.toDataURL("image/jpeg", 0.7);
                      socket.send(JSON.stringify({ "video_frame": base64Frame }));
                  }
              }, 2000); 
          }

          statusIndicator.className = "green";
          statusIndicator.textContent = `PROTOCOL ACTIVE: ${selectedTemplate}`;
        } catch (mediaError) {
          logEvent(`[FAULT] Sensor array failed: ${mediaError.message}`);
          statusIndicator.className = "red";
          statusIndicator.textContent = "HARDWARE REJECTED";
        }
      };

      socket.onmessage = async (event) => {
        if (event.data instanceof Blob) {
            const arrayBuffer = await event.data.arrayBuffer();
            const int16Array = new Int16Array(arrayBuffer);
            const float32Array = new Float32Array(int16Array.length);
            
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / 32768.0;
            }

            const audioBuffer = playbackContext.createBuffer(1, float32Array.length, 24000);
            audioBuffer.getChannelData(0).set(float32Array);

            const source = playbackContext.createBufferSource();
            source.buffer = audioBuffer;
            
            // Route to speakers AND recording mixer
            source.connect(playbackContext.destination);
            if (window.recordingDestination) {
                source.connect(window.recordingDestination);
            }

            source.onended = () => {
                const idx = activeAudioNodes.indexOf(source);
                if (idx > -1) activeAudioNodes.splice(idx, 1);
                if (activeAudioNodes.length === 0) {
                    window.charonSpeakingTimeout = setTimeout(() => {
                        window.lastAgentSpeechTime = Date.now(); 
                        window.isCharonSpeaking = false;
                    }, 300);
                }
            };
            
            if (window.charonSpeakingTimeout) {
                clearTimeout(window.charonSpeakingTimeout);
                window.charonSpeakingTimeout = null;
            }

            activeAudioNodes.push(source);
            window.isCharonSpeaking = true;

            const currentTime = playbackContext.currentTime;
            if (nextPlaybackTime < currentTime) {
                nextPlaybackTime = currentTime + 0.01;
            }
            
            source.start(nextPlaybackTime);
            nextPlaybackTime += audioBuffer.duration;
            return;
        }

        const data = JSON.parse(event.data);
        
        if (data.system_event) {
          if (data.system_event === "interrupted" || data.system_event === "flush") {
              window.stopAgentAudio();
              return;
          }
          if (data.system_event.includes("Mounting")) logEvent("Core Orchestrator Engaged.");
          else if (data.system_event.includes("initialized")) logEvent("Multi-Agent Council synchronized.");
          else logEvent(`System Update: ${data.system_event}`);
          return;
        }

        if (data.indicator && !data.async_results) {
          logEvent(`Live Evaluation: ${data.message}`);
          statusIndicator.className = data.indicator;
          statusIndicator.textContent = data.message;
        }
        
        if (data.async_results) {
          if (data.async_results.pacing) {
            const pace = data.async_results.pacing;
            if (pace.indicator !== "green" && pace.indicator !== "white") {
              logEvent(`Telemetry Warning: ${pace.message}`);
            }
            statusIndicator.className = pace.indicator;
            statusIndicator.textContent = pace.message;
          }
          
          if (data.async_results.council && Array.isArray(data.async_results.council)) {
            data.async_results.council.forEach(evalResult => {
                if (evalResult && evalResult.message) {
                    logEvent(`Council Consensus: ${evalResult.message}`);
                    if (evalResult.indicator !== "green") {
                        statusIndicator.className = evalResult.indicator;
                        statusIndicator.textContent = evalResult.message;
                    }
                }
            });
          }
        }
      };

      socket.onclose = (e) => {
        logEvent(`Matrix link disconnected.`);
        if(e.code !== 1000 && e.code !== 1001) {
             statusIndicator.className = "red";
             statusIndicator.textContent = "LINK SEVERED";
        }
        terminateSessionUI();
      };

      socket.onerror = (error) => {
        logEvent("Engine fault detected. Matrix connection terminated.");
        statusIndicator.className = "red";
        statusIndicator.textContent = "ENGINE FAULT";
        terminateSessionUI();
      };

    } catch (error) {
      statusIndicator.className = "red";
      statusIndicator.textContent = "SYSTEM FAULT";
      logEvent(`[CRITICAL] Engine Crash: ${error.message}`);
      terminateSessionUI();
    }
  }

  function terminateSessionUI() {
    isSessionActive = false;
    sessionToggle.textContent = "START SESSION";
    statusIndicator.className = "white";
    statusIndicator.textContent = "SYSTEM STANDBY";
    idlePanel.style.display = "flex";
    activeSessionPanel.style.display = "none";

    stopAudioCapture();
    window.stopAgentAudio();

    // Finalize recording if active
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        logEvent("Recording finalized and downloading.");
    }
    mediaRecorder = null;
    window.recordingDestination = null;
    
    if (window.vadInterval) {
        clearInterval(window.vadInterval);
        window.vadInterval = null;
    }
    if (window.audioCtx) {
        window.audioCtx.close();
        window.audioCtx = null;
    }
    if (window.videoAuditInterval) {
        clearInterval(window.videoAuditInterval);
        window.videoAuditInterval = null;
    }
    
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    if (activeStream) {
      activeStream.getTracks().forEach(track => track.stop());
      videoFeed.srcObject = null;
    }
  }

  sessionToggle.addEventListener("click", () => {
    if (isSessionActive) {
      logEvent("Manual termination sequence initiated...");
      terminateSessionUI();
    } else {
      startSession();
    }
  });
});