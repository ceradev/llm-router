export function getTrailVisual(indexFromTop: number) {
  // Top item is the most important; older items drift down, blur, and fade away.
  if (indexFromTop <= 0) return { opacity: 1, blurPx: 0 }
  if (indexFromTop === 1) return { opacity: 0.72, blurPx: 0.6 }
  if (indexFromTop === 2) return { opacity: 0.46, blurPx: 1.1 }
  return { opacity: 0.26, blurPx: 1.8 }
}

