/* AgriNovva — camera.js
   Photo capture. Uses the Capacitor native bridge (window.Capacitor.Plugins.Camera)
   on Android — no bundler required, src/ is served directly. Falls back to an
   HTML file input on web/PWA. Returns a JPEG data URL. */

export async function capturePhoto(fromGallery = false) {
  const Camera = window.Capacitor?.Plugins?.Camera;

  if (Camera) {
    try {
      const image = await Camera.getPhoto({
        quality: 85,
        resultType: 'dataUrl',
        source: fromGallery ? 'photos' : 'camera',
        correctOrientation: true
      });
      return image.dataUrl;
    } catch (err) {
      if (String(err?.message).includes('cancel')) throw new Error('cancelled');
      throw err;
    }
  }

  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    if (!fromGallery) input.capture = 'environment';
    input.onchange = () => {
      const file = input.files && input.files[0];
      if (!file) { reject(new Error('cancelled')); return; }
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    };
    input.oncancel = () => {
      reject(new Error('cancelled'));
    };
    input.click();
  });
}

export function isNative() {
  return typeof window !== 'undefined' && Boolean(window.Capacitor?.isNativePlatform?.());
}