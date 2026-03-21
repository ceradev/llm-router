import { useReducedMotion } from 'framer-motion';
import { lazy, Suspense } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

const ShaderWavesScene = lazy(() =>
  import('./ShaderWavesScene').then((m) => ({ default: m.ShaderWavesScene })),
);

export function ShaderWavesBackground() {
  const reduce = useReducedMotion();
  const { theme } = useTheme();
  const colorScheme = theme === 'dark' ? 'dark' : 'light';
  const animate = reduce ? 'off' : 'on';

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-(--bg-base)"
      aria-hidden
    >
      <Suspense fallback={null}>
        <ShaderWavesScene animate={animate} colorScheme={colorScheme} />
      </Suspense>
    </div>
  );
}
