# TUXInput Migration Guide

## Old TUX Input Component

The old TUX Input component was used as follows:

```tsx
import { TUXInput } from "@byted-tiktok/tux-components";
```

### Usage Example

```tsx
<TUXInput
  placeholder="Enter your text"
  value={inputValue}
  onChange={handleChange}
  size="medium"
/>
```

## New TUX Input Component

The new TUX Input component should be used as follows:

```tsx
import { Input } from "@byted-tiktok/tux-web";
```

### Usage Example

```tsx
<Input
  placeholder="Enter your text"
  value={inputValue}
  onChange={handleChange}
  variant="outlined"
/>
```

## Migration Notes

- Component name changed from `TUXInput` to `Input`
- Import path changed from `@byted-tiktok/tux-components` to `@byted-tiktok/tux-web`
- The `size` prop has been replaced with `variant` prop
- Supported variants: `outlined`, `filled`, `standard`