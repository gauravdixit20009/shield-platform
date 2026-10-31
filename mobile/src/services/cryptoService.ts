import * as Crypto from 'expo-crypto';
import * as FileSystem from 'expo-file-system';

export async function computeFileHashSHA512(fileUri: string): Promise<string> {
  const fileContent = await FileSystem.readAsStringAsync(fileUri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  return await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA512, fileContent);
}

export async function generateCustodySignature(
  officerBadge: string,
  timestamp: string,
  fileHash: string
): Promise<string> {
  const payload = `${officerBadge}|${timestamp}|${fileHash}`;
  return await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, payload);
}
