let device = null;
let activeConnection = null;
let defaultPatientId = null;

const log = (msg) => {
  const el = document.getElementById("log");
  el.textContent += `${new Date().toLocaleTimeString()}  ${msg}\n`;
  el.scrollTop = el.scrollHeight;
};

async function loadDefaultPatient() {
  const res = await fetch("/api/patients");
  const [patient] = await res.json();
  defaultPatientId = patient.id;
  const input = document.getElementById("phoneNumber");
  if (!input.value) input.value = patient.phone_number;
}

async function setupDevice() {
  const res = await fetch("/api/token");
  const { token } = await res.json();
  device = new Twilio.Device(token, { logLevel: 1 });

  device.on("registered", () => log("Softphone ready"));
  device.on("error", (e) => log(`Device error: ${e.message}`));
  device.on("disconnect", () => {
    log("Call ended");
    activeConnection = null;
    document.getElementById("callBtn").disabled = false;
    document.getElementById("hangupBtn").disabled = true;
    document.getElementById("muteBtn").disabled = true;
  });

  await device.register();
}

const E164_PATTERN = /^\+[1-9]\d{6,14}$/;

async function placeCall() {
  const phoneNumber = document.getElementById("phoneNumber").value.trim();
  if (!E164_PATTERN.test(phoneNumber)) {
    log(`Invalid phone number: ${phoneNumber} (use E.164 format, e.g. +15551234567)`);
    return;
  }

  log(`Calling ${phoneNumber}...`);
  activeConnection = await device.connect({ params: { phone_number: phoneNumber } });
  document.getElementById("callBtn").disabled = true;
  document.getElementById("hangupBtn").disabled = false;
  document.getElementById("muteBtn").disabled = false;
}

function hangup() {
  if (activeConnection) activeConnection.disconnect();
}

function toggleMute() {
  if (!activeConnection) return;
  const muted = !activeConnection.isMuted();
  activeConnection.mute(muted);
  log(muted ? "Muted" : "Unmuted");
}

async function refreshRecordingStatus() {
  const res = await fetch(`/api/patients/${defaultPatientId}/calls`);
  const calls = await res.json();
  const el = document.getElementById("recordingStatus");
  if (calls.length === 0) {
    el.textContent = "(no calls yet)";
    return;
  }
  const latest = calls[calls.length - 1];
  if (!latest.recording_sid) {
    el.textContent = `Call status: ${latest.status}\nRecording: not ready yet`;
    return;
  }
  el.textContent = `Call status: ${latest.status}\nRecording SID: ${latest.recording_sid}\nRecording URL: ${latest.recording_url}\n\n(download it with your Twilio Account SID/Auth Token for playback)`;
}

document.getElementById("callBtn").addEventListener("click", placeCall);
document.getElementById("hangupBtn").addEventListener("click", hangup);
document.getElementById("muteBtn").addEventListener("click", toggleMute);
document.getElementById("refreshStatusBtn").addEventListener("click", refreshRecordingStatus);

loadDefaultPatient();
setupDevice();
