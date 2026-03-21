import { ShaderGradient, ShaderGradientCanvas } from '@shadergradient/react';

export type ShaderWavesSceneProps = {
  animate: 'on' | 'off';
  colorScheme: 'dark' | 'light';
};

const SCHEME = {
  dark: {
    color1: '#0b0f1a',
    color2: '#1e3a8a',
    color3: '#3b82f6',
    brightness: 0.95,
    uStrength: 2.2,
    uFrequency: 3.2,
  },
  /** ~80% base claro, acentos #1E40AF / #3B82F6 más suaves para el plano */
  light: {
    color1: '#f1f5f9',
    color2: '#60a5fa',
    color3: '#1d4ed8',
    brightness: 1.12,
    uStrength: 1.65,
    uFrequency: 2.9,
  },
} as const;

/**
 * WebGL scene — loaded only via dynamic import from ShaderWavesBackground.
 */
export function ShaderWavesScene({ animate, colorScheme }: Readonly<ShaderWavesSceneProps>) {
  const c = SCHEME[colorScheme];

  return (
    <ShaderGradientCanvas
      className="absolute inset-0 h-full w-full"
      style={{ position: 'absolute', inset: 0 }}
      pixelDensity={1.25}
      fov={45}
      pointerEvents="none"
      lazyLoad
      threshold={0}
    >
      <ShaderGradient
        control="props"
        type="waterPlane"
        shader="defaults"
        animate={animate}
        grain="off"
        color1={c.color1}
        color2={c.color2}
        color3={c.color3}
        uSpeed={0.32}
        uStrength={c.uStrength}
        uFrequency={c.uFrequency}
        brightness={c.brightness}
        cDistance={5}
        cPolarAngle={118}
        cAzimuthAngle={178}
        lightType="3d"
      />
    </ShaderGradientCanvas>
  );
}
