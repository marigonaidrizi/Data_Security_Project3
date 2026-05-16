document.addEventListener("DOMContentLoaded", () => {
  const refreshButton = document.getElementById("refresh-files");
  const fileList = document.getElementById("file-list");
  const searchInput = document.getElementById("file-search");
  let currentFiles = [];

  async function initialize() {
    window.SecureApp.setStatus("Initializing", "Generating client RSA keys...");
    await window.SecureCrypto.generateClientKeys();
    await window.SecureCrypto.fetchServerPublicKey();
    window.SecureApp.setStatus("Ready", "Client keys generated. File list loading...");
    await loadFiles();
  }

  function renderFiles(files) {
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const visibleFiles = query
      ? files.filter((file) => file.filename.toLowerCase().includes(query))
      : files;
    const total = document.getElementById("files-total-count");
    const verified = document.getElementById("files-verified-count");
    if (total) {
      total.textContent = files.length;
    }
    if (verified) {
      verified.textContent = window.SecureApp.verifiedCount(files);
    }
    if (!files.length) {
      fileList.innerHTML = '<div class="empty-state">No files are available yet.</div>';
      return;
    }
    fileList.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th>Uploaded</th>
            <th>Size</th>
            <th>Downloads</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>${window.SecureApp.fileTableRows(visibleFiles, true)}</tbody>
      </table>
    `;
    for (const button of fileList.querySelectorAll("[data-download-id]")) {
      button.addEventListener("click", () => downloadFile(button.dataset.downloadId));
    }
  }

  async function loadFiles() {
    fileList.textContent = "Loading files...";
    try {
      const data = await window.SecureApp.fetchJson("/api/files");
      currentFiles = data.files || [];
      renderFiles(currentFiles);
      window.SecureApp.setStatus("Ready", `Loaded ${currentFiles.length} file(s).`);
    } catch (error) {
      fileList.innerHTML = `<p class="error">${error.message}</p>`;
      window.SecureApp.setStatus("Failed", error.message);
    }
  }

  async function downloadFile(fileId) {
    try {
      window.SecureApp.setStatus("Requesting", "Sending client public key to server...");
      await window.SecureCrypto.generateClientKeys();
      const clientPublicKey = await window.SecureCrypto.exportEncryptionPublicKeyPem();
      const packageData = await window.SecureApp.fetchJson(`/api/files/download/${fileId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_public_key: clientPublicKey }),
      });

      window.SecureApp.setStatus("Decrypting", "Decrypting AES key and file payload.", true);
      const encryptedAesKey = window.SecureCrypto.base64ToArrayBuffer(packageData.encrypted_aes_key);
      const rawAesKey = await window.SecureCrypto.decryptAesKey(encryptedAesKey);
      const aesKey = await window.SecureCrypto.importAesKey(rawAesKey);
      const nonce = window.SecureCrypto.base64ToArrayBuffer(packageData.aes_nonce);
      const encryptedFile = window.SecureCrypto.base64ToArrayBuffer(packageData.encrypted_file);
      const plaintext = await window.SecureCrypto.decryptFile(encryptedFile, aesKey, nonce);

      window.SecureApp.setStatus("Verifying", "Checking SHA-256 hash and server signature.", true);
      const calculatedHash = await window.SecureCrypto.sha256(plaintext);
      const calculatedHashHex = window.SecureCrypto.arrayBufferToHex(calculatedHash);
      if (calculatedHashHex !== packageData.file_hash.toLowerCase()) {
        throw new Error("Downloaded file hash does not match server hash.");
      }

      const serverVerificationKey = await window.SecureCrypto.importVerificationPublicKey(packageData.server_public_key);
      const signature = window.SecureCrypto.base64ToArrayBuffer(packageData.signature);
      const verified = await window.SecureCrypto.verifyHashSignature(
        serverVerificationKey,
        signature,
        window.SecureCrypto.hexToArrayBuffer(packageData.file_hash),
      );
      if (!verified) {
        throw new Error("Server signature verification failed.");
      }

      window.SecureCrypto.saveArrayBuffer(packageData.filename, plaintext);
      window.SecureApp.setStatus("Complete", `Downloaded, decrypted, and verified ${packageData.filename}.`);
      await loadFiles();
    } catch (error) {
      const code = error.payload && error.payload.error ? ` (${error.payload.error})` : "";
      window.SecureApp.setStatus("Failed", `${error.message}${code}`);
    }
  }

  refreshButton.addEventListener("click", loadFiles);
  if (searchInput) {
    searchInput.addEventListener("input", () => renderFiles(currentFiles));
  }
  initialize().catch((error) => {
    window.SecureApp.setStatus("Initialization Failed", error.message);
  });
});
