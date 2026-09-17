// Turns the plaintext export the server hands back into a downloadable,
// self-contained encrypted file, and back. Everything here runs in the
// browser; the seed and passphrase never leave it.
import { mnemonicToSeed } from "./bip39";

const FILE_MAGIC = "CRYPTMASTER_BACKUP_V1";
const HKDF_INFO = new TextEncoder().encode("cryptmaster-backup-v1");

interface BackupFile {
  magic: string;
  hkdf_salt: string; // base64
  nonce: string; // base64
  ciphertext: string; // base64
}

function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function fromBase64(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function deriveAesKey(bip39Seed: Uint8Array, hkdfSalt: Uint8Array): Promise<CryptoKey> {
  // See bip39.ts's sha256() comment re: the BufferSource casts below.
  const seedKey = await crypto.subtle.importKey(
    "raw",
    bip39Seed as BufferSource,
    { name: "HKDF" },
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "HKDF", hash: "SHA-256", salt: hkdfSalt as BufferSource, info: HKDF_INFO },
    seedKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export async function encryptBackup(data: unknown, words: string[], passphrase: string): Promise<Blob> {
  const bip39Seed = await mnemonicToSeed(words, passphrase);
  const hkdfSalt = crypto.getRandomValues(new Uint8Array(16));
  const key = await deriveAesKey(bip39Seed, hkdfSalt);
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(data));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce as BufferSource },
    key,
    plaintext as BufferSource,
  );

  const file: BackupFile = {
    magic: FILE_MAGIC,
    hkdf_salt: toBase64(hkdfSalt),
    nonce: toBase64(nonce),
    ciphertext: toBase64(new Uint8Array(ciphertext)),
  };
  return new Blob([JSON.stringify(file, null, 2)], { type: "application/json" });
}

export class BackupDecryptionError extends Error {}

export async function decryptBackup(fileText: string, words: string[], passphrase: string): Promise<unknown> {
  let file: BackupFile;
  try {
    file = JSON.parse(fileText);
  } catch {
    throw new BackupDecryptionError("This doesn't look like a Crypt Master backup file (not valid JSON).");
  }
  if (file.magic !== FILE_MAGIC) {
    throw new BackupDecryptionError("This doesn't look like a Crypt Master backup file (wrong format marker).");
  }

  const bip39Seed = await mnemonicToSeed(words, passphrase);
  const hkdfSalt = fromBase64(file.hkdf_salt);
  const key = await deriveAesKey(bip39Seed, hkdfSalt);
  const nonce = fromBase64(file.nonce);
  const ciphertext = fromBase64(file.ciphertext);

  try {
    const plaintext = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: nonce as BufferSource },
      key,
      ciphertext as BufferSource,
    );
    return JSON.parse(new TextDecoder().decode(plaintext));
  } catch {
    throw new BackupDecryptionError(
      "Could not decrypt this backup. Check that the 24 words and passphrase are exactly right.",
    );
  }
}
