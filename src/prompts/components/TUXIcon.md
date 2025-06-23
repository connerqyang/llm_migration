# TUXIcon Migration Guide

## Old TUX Icon Components

### Import Examples

The old TUX Icon components were imported as follows:

```tsx
import { TUXIconStarRing } from "@byted-tiktok/tux-components";
```

Or:

```tsx
import { TUXIconStarRing, TUXIconChevronUp, TUXIconHeadset } from '@byted-tiktok/tux-icons';
```

### Props Interface

```tsx
interface TUXIconProps { 
  color?: string; // color name 
  size?: number; // unit: px 
  circleBackground?: { 
    backgroundColor: string; // color name 
    circleSize: number; // unit: px 
  } 
}
```

### Usage Examples

```tsx
<TUXIconStarRing color='Link' size={48} />

<TUXIconStarRing color='Positive' size={32} />

<TUXIconStarRing color='Positive' size={32} circleBackground={{ 
  circleSize: 72, 
  backgroundColor: 'BGView' 
}} />

<TUXIconColorTikTokLogoDark size={48} />
```

## New TUX Icon Components

### Import Example

The new TUX Icon components should be imported as follows:

```tsx
import { IconStarRing } from '@byted-tiktok/tux-icons';
import { getColorCSSVar } from '@byted-tiktok/tux-web/canary';
```

### Usage Example

```tsx
const color = getColorCSSVar('UITextPrimaryDisplay');
return <IconStarRing fontSize={48} color={color} />;
```

## Migration Notes

- The naming convention has changed: `TUXIcon` prefix is now replaced with `Icon` prefix (e.g., `TUXIcon3ptDuet` → `Icon3ptDuet`)
- Import path has changed: use `@byted-tiktok/tux-icons` for icons and `@byted-tiktok/tux-web/canary` for color utilities
- Props have changed:
  - `size` prop is now `fontSize`
  - `color` prop now expects a CSS variable value instead of a color name (use `getColorCSSVar` helper)
  - `circleBackground` prop is no longer supported
- For color values, use the `getColorCSSVar` utility to convert color names to CSS variables