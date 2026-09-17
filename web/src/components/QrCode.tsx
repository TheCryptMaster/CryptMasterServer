import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";

export function QrCode({ data }: { data: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, data, { width: 220, margin: 1 }).catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Failed to render QR code"),
    );
  }, [data]);

  return (
    <div className="qr-code">
      <canvas ref={canvasRef} />
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
