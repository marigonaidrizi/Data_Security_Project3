document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const button = document.getElementById("upload-button");

  async function initialize() {
    window.SecureApp.setStatus("Initializing", "Generating client RSA keys...");
    await window.SecureCrypto.generateClientKeys();
    window.SecureApp.setStatus("Fetching Server Key", "Requesting server public key...");
    await window.SecureCrypto.fetchServerPublicKey();
    window.SecureApp.setStatus("Ready", "Client keys generated. Server public key imported.");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      window.SecureApp.setStatus("No File", "Choose a file before uploading.");
      return;
    }

    button.disabled = true;
    try {
      window.SecureApp.setStatus("Encrypting", `Reading ${file.name}...`);
      await window.SecureCrypto.generateClientKeys();
      await window.SecureCrypto.fetchServerPublicKey();

      const fileBuffer = await file.arrayBuffer();
      const aesKey = await window.SecureCrypto.generateAesKey();
      const nonce = window.SecureCrypto.generateNonce();
      const encryptedFile = await window.SecureCrypto.encryptFile(fileBuffer, aesKey, nonce);
      window.SecureApp.setStatus("Hashing", "Calculating SHA-256 hash.", true);

      const hashBuffer = await window.SecureCrypto.sha256(fileBuffer);
      const fileHash = window.SecureCrypto.arrayBufferToHex(hashBuffer);
      const signature = await window.SecureCrypto.signHash(hashBuffer);
      window.SecureApp.setStatus("Packaging", "Signing hash and encrypting AES key.", true);

      const rawAesKey = await window.SecureCrypto.exportRawAesKey(aesKey);
      const encryptedAesKey = await window.SecureCrypto.encryptAesKey(rawAesKey);
      const clientPublicKey = await window.SecureCrypto.exportSigningPublicKeyPem();

      const payload = {
        filename: file.name,
        client_public_key: clientPublicKey,
        encrypted_aes_key: window.SecureCrypto.arrayBufferToBase64(encryptedAesKey),
        aes_nonce: window.SecureCrypto.arrayBufferToBase64(nonce),
        encrypted_file: window.SecureCrypto.arrayBufferToBase64(encryptedFile),
        file_hash: fileHash,
        signature: window.SecureCrypto.arrayBufferToBase64(signature),
        original_size: file.size,
        timestamp: new Date().toISOString(),
      };

      window.SecureApp.setStatus("Uploading", "Sending encrypted package to server.", true);
      const result = await window.SecureApp.fetchJson("/api/files/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      window.SecureApp.setStatus(
        "Complete",
        `Upload stored as ${result.file_id}. Hash verified: ${result.hash_verified}. Signature verified: ${result.signature_verified}.`,
      );
      form.reset();
    } catch (error) {
      const code = error.payload && error.payload.error ? ` (${error.payload.error})` : "";
      window.SecureApp.setStatus("Failed", `${error.message}${code}`);
    } finally {
      button.disabled = false;
    }
  });

  initialize().catch((error) => {
    window.SecureApp.setStatus("Initialization Failed", error.message);
  });
});
