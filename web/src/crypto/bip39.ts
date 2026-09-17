// Standard BIP-39: 256 bits of entropy -> 24 words, with the passphrase
// acting as the mnemonic's own "25th word" (exactly the hardware-wallet
// convention), all done with native WebCrypto -- no third-party library, so
// this is one self-contained, auditable file instead of a supply-chain
// dependency for the single most security-critical feature in the app.
import { WORDLIST } from "./wordlist";

const ENTROPY_BYTES = 32; // 256 bits -> 24 words
const WORD_COUNT = 24;

function bytesToBinary(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(2).padStart(8, "0"))
    .join("");
}

async function sha256(bytes: Uint8Array): Promise<Uint8Array> {
  // TS 5.7's DOM lib narrows BufferSource to Uint8Array<ArrayBuffer> specifically;
  // a plain `Uint8Array` parameter type doesn't satisfy that at the call site.
  const digest = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return new Uint8Array(digest);
}

export async function generateMnemonic(): Promise<string[]> {
  const entropy = crypto.getRandomValues(new Uint8Array(ENTROPY_BYTES));
  return entropyToMnemonic(entropy);
}

export async function entropyToMnemonic(entropy: Uint8Array): Promise<string[]> {
  const checksumBits = entropy.length / 4; // bits, per BIP-39 (CS = ENT / 32)
  const hash = await sha256(entropy);
  const entropyBits = bytesToBinary(entropy);
  const checksumBinary = bytesToBinary(hash).slice(0, checksumBits);
  const bits = entropyBits + checksumBinary;

  const words: string[] = [];
  for (let i = 0; i < bits.length / 11; i++) {
    const chunk = bits.slice(i * 11, (i + 1) * 11);
    words.push(WORDLIST[parseInt(chunk, 2)]);
  }
  return words;
}

export interface MnemonicValidation {
  valid: boolean;
  error?: string;
}

export async function validateMnemonic(words: string[]): Promise<MnemonicValidation> {
  if (words.length !== WORD_COUNT) {
    return { valid: false, error: `Expected ${WORD_COUNT} words, got ${words.length}` };
  }
  const indices: number[] = [];
  for (const word of words) {
    const idx = WORDLIST.indexOf(word.trim().toLowerCase());
    if (idx === -1) {
      return { valid: false, error: `"${word}" is not a valid recovery word` };
    }
    indices.push(idx);
  }
  const bits = indices.map((i) => i.toString(2).padStart(11, "0")).join("");
  const entropyBits = bits.slice(0, 256);
  const checksumBits = bits.slice(256);
  const entropyBytes = new Uint8Array(32);
  for (let i = 0; i < 32; i++) {
    entropyBytes[i] = parseInt(entropyBits.slice(i * 8, i * 8 + 8), 2);
  }
  const hash = await sha256(entropyBytes);
  const expectedChecksum = bytesToBinary(hash).slice(0, 8);
  if (checksumBits !== expectedChecksum) {
    return { valid: false, error: "Checksum mismatch -- one or more words may be wrong or out of order" };
  }
  return { valid: true };
}

/** Standard BIP-39 mnemonic-to-seed: PBKDF2-HMAC-SHA512(mnemonic, "mnemonic"+passphrase, 2048 iterations) -> 64 bytes. */
export async function mnemonicToSeed(words: string[], passphrase: string): Promise<Uint8Array> {
  const mnemonic = words.join(" ").normalize("NFKD");
  const salt = ("mnemonic" + passphrase).normalize("NFKD");
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(mnemonic),
    { name: "PBKDF2" },
    false,
    ["deriveBits"],
  );
  const seedBits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: new TextEncoder().encode(salt), iterations: 2048, hash: "SHA-512" },
    keyMaterial,
    512,
  );
  return new Uint8Array(seedBits);
}
