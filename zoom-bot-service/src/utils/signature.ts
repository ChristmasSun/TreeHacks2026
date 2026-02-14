/**
 * Zoom Meeting SDK Signature Generation
 */
import crypto from 'crypto';

export function generateSignature(
  sdkKey: string,
  sdkSecret: string,
  meetingNumber: string,
  role: 0 | 1 = 0 // 0 = participant, 1 = host
): string {
  const timestamp = new Date().getTime() - 30000; // 30 seconds ago for clock skew
  const msg = Buffer.from(sdkKey + meetingNumber + timestamp + role).toString('base64');
  const hash = crypto.createHmac('sha256', sdkSecret).update(msg).digest('base64');
  const signature = Buffer.from(`${sdkKey}.${meetingNumber}.${timestamp}.${role}.${hash}`).toString('base64');

  return signature;
}

/**
 * Generate JWT signature for Zoom Meeting SDK
 * This is the newer method recommended by Zoom
 */
export function generateJWT(
  sdkKey: string,
  sdkSecret: string,
  meetingNumber: string,
  role: 0 | 1 = 0
): string {
  // Note: For production, use a proper JWT library like 'jsonwebtoken'
  // This is a simplified version

  const iat = Math.floor(Date.now() / 1000) - 30;
  const exp = iat + 60 * 60 * 2; // 2 hours

  const header = {
    alg: 'HS256',
    typ: 'JWT'
  };

  const payload = {
    sdkKey: sdkKey,
    mn: meetingNumber,
    role: role,
    iat: iat,
    exp: exp,
    appKey: sdkKey,
    tokenExp: exp
  };

  // Encode header and payload
  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');

  // Create signature
  const signatureInput = `${encodedHeader}.${encodedPayload}`;
  const signature = crypto
    .createHmac('sha256', sdkSecret)
    .update(signatureInput)
    .digest('base64url');

  return `${encodedHeader}.${encodedPayload}.${signature}`;
}
