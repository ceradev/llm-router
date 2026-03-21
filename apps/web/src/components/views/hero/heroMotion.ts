import type { Transition } from 'framer-motion';

export const heroContainerTransition: Transition = { duration: 0.35 };

export const heroHeadlineTransition: Transition = {
  duration: 0.45,
  ease: 'easeOut',
  delay: 0.05,
};

export const heroPromptBlockTransition: Transition = {
  duration: 0.45,
  ease: 'easeOut',
  delay: 0.12,
};

export const advancedToggleThumbSpring: Transition = {
  type: 'spring',
  stiffness: 500,
  damping: 32,
};

export const analyseButtonSpring: Transition = {
  type: 'spring',
  stiffness: 420,
  damping: 25,
};

export const analyseShineTransition: Transition = { duration: 0.6 };

export const analyseHoverWhile = {
  scale: 1.02,
  boxShadow: '0 0 32px rgba(139,92,246,0.35), 0 0 48px rgba(59,130,246,0.2)',
} as const;

export const analyseTapWhile = { scale: 0.97 } as const;
