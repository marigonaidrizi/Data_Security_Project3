(function () {
  const state = {
    encryptionKeyPair: null,
    signingKeyPair: null,
    serverPublicKeyPem: null,
    serverEncryptionKey: null,
    serverVerificationKey: null,
  };

  function requireWebCrypto() {
    if (!window.crypto || !window.crypto.subtle) {
      throw new Error("Web Crypto API is unavailable. Open the client through http://127.0.0.1:8000/client/.");
    }
  }

  function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
  }

  function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function arrayBufferToHex(buffer) {
    return Array.from(new Uint8Array(buffer))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  function hexToArrayBuffer(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i += 1) {
      bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
    }
    return bytes.buffer;
  }

  function pemToArrayBuffer(pem) {
    const base64 = pem
      .replace(/-----BEGIN PUBLIC KEY-----/g, "")
      .replace(/-----END PUBLIC KEY-----/g, "")
      .replace(/\s+/g, "");
    return base64ToArrayBuffer(base64);
  }

  function arrayBufferToPem(buffer, label) {
    const base64 = arrayBufferToBase64(buffer);
    const lines = base64.match(/.{1,64}/g) || [];
    return `-----BEGIN ${label}-----\n${lines.join("\n")}\n-----END ${label}-----`;
  }

  async function generateClientKeys() {
    requireWebCrypto();
    if (state.encryptionKeyPair && state.signingKeyPair) {
      return state;
    }

    state.encryptionKeyPair = await crypto.subtle.generateKey(
      {
        name: "RSA-OAEP",
        modulusLength: 3072,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: "SHA-256",
      },
      true,
      ["encrypt", "decrypt"],
    );

    state.signingKeyPair = await crypto.subtle.generateKey(
      {
        name: "RSA-PSS",
        modulusLength: 3072,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: "SHA-256",
      },
      true,
      ["sign", "verify"],
    );

    return state;
  }

  async function exportEncryptionPublicKeyPem() {
    await generateClientKeys();
    const spki = await crypto.subtle.exportKey("spki", state.encryptionKeyPair.publicKey);
    return arrayBufferToPem(spki, "PUBLIC KEY");
  }

  async function exportSigningPublicKeyPem() {
    await generateClientKeys();
    const spki = await crypto.subtle.exportKey("spki", state.signingKeyPair.publicKey);
    return arrayBufferToPem(spki, "PUBLIC KEY");
  }

  async function fetchServerPublicKey() {
    const data = await window.SecureApp.fetchJson("/api/crypto/server-public-key");
    state.serverPublicKeyPem = data.public_key;
    state.serverEncryptionKey = await crypto.subtle.importKey(
      "spki",
      pemToArrayBuffer(data.public_key),
      { name: "RSA-OAEP", hash: "SHA-256" },
      false,
      ["encrypt"],
    );
    state.serverVerificationKey = await importVerificationPublicKey(data.public_key);
    return data;
  }

  async function importVerificationPublicKey(publicKeyPem) {
    return crypto.subtle.importKey(
      "spki",
      pemToArrayBuffer(publicKeyPem),
      { name: "RSA-PSS", hash: "SHA-256" },
      false,
      ["verify"],
    );
  }

  async function generateAesKey() {
    return crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  }

  async function importAesKey(rawKey) {
    return crypto.subtle.importKey("raw", rawKey, { name: "AES-GCM" }, false, ["decrypt"]);
  }

  function generateNonce() {
    const nonce = new Uint8Array(12);
    crypto.getRandomValues(nonce);
    return nonce;
  }

  async function encryptFile(fileBuffer, aesKey, nonce) {
    return crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, aesKey, fileBuffer);
  }

  async function decryptFile(encryptedBuffer, aesKey, nonceBuffer) {
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: new Uint8Array(nonceBuffer) }, aesKey, encryptedBuffer);
  }

  async function sha256(buffer) {
    return crypto.subtle.digest("SHA-256", buffer);
  }

  async function signHash(hashBuffer) {
    await generateClientKeys();
    return crypto.subtle.sign(
      { name: "RSA-PSS", saltLength: 32 },
      state.signingKeyPair.privateKey,
      hashBuffer,
    );
  }

  async function verifyHashSignature(publicKey, signatureBuffer, hashBuffer) {
    return crypto.subtle.verify(
      { name: "RSA-PSS", saltLength: 32 },
      publicKey,
      signatureBuffer,
      hashBuffer,
    );
  }

  async function encryptAesKey(rawAesKey) {
    if (!state.serverEncryptionKey) {
      await fetchServerPublicKey();
    }
    return crypto.subtle.encrypt({ name: "RSA-OAEP" }, state.serverEncryptionKey, rawAesKey);
  }

  async function decryptAesKey(encryptedAesKeyBuffer) {
    await generateClientKeys();
    return crypto.subtle.decrypt(
      { name: "RSA-OAEP" },
      state.encryptionKeyPair.privateKey,
      encryptedAesKeyBuffer,
    );
  }

  async function exportRawAesKey(aesKey) {
    return crypto.subtle.exportKey("raw", aesKey);
  }

  function saveArrayBuffer(filename, buffer) {
    const blob = new Blob([buffer]);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  window.SecureCrypto = {
    state,
    generateClientKeys,
    fetchServerPublicKey,
    exportEncryptionPublicKeyPem,
    exportSigningPublicKeyPem,
    importVerificationPublicKey,
    generateAesKey,
    importAesKey,
    generateNonce,
    encryptFile,
    decryptFile,
    sha256,
    signHash,
    verifyHashSignature,
    encryptAesKey,
    decryptAesKey,
    exportRawAesKey,
    saveArrayBuffer,
    arrayBufferToBase64,
    base64ToArrayBuffer,
    arrayBufferToHex,
    hexToArrayBuffer,
  };
})();
