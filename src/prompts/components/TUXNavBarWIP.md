# TUXNavBar Migration Guide

## Old TUX Navigation Components

### Import Examples

```tsx
import { TUXTitleBar } from "@byted-tiktok/tux-h5";
import { TUXAppBar } from "@byted-tiktok/tux-h5";
import { TUXNavBar } from "@byted-tiktok/tux-h5";
```

### TUXTitleBar Props Interface

```tsx
interface TUXTitleBarProps {
  title?: string;                // Title text
  leftText?: string;             // Left action text
  rightText?: string;            // Right action text
  onLeftClick?: () => void;      // Left action callback
  onRightClick?: () => void;     // Right action callback
  leftIcon?: ReactNode;          // Custom left icon
  rightIcon?: ReactNode;         // Custom right icon
  backgroundColor?: string;      // Background color
  // Additional props may be available
}
```

### Usage Examples

```tsx
// TUXTitleBar example
<TUXTitleBar
  title="Page Title"
  leftText="Back"
  onLeftClick={handleBack}
  rightText="Done"
  onRightClick={handleDone}
/>

// TUXTitleBar with icons
<TUXTitleBar
  title="Page Title"
  leftIcon={<TUXIconChevronLeft />}
  onLeftClick={handleBack}
  rightIcon={<TUXIconCheck />}
  onRightClick={handleDone}
/>
```

## New TUXNavBar Component

### Import Example

```tsx
import { TUXNavBar, TUXNavBarIconAction } from "@byted-tiktok/tux-web/canary";
import { IconChevronLeftOffsetLTR, IconCheck } from "@byted-tiktok/tux-icons";
```

### Props Interface

```tsx
interface TUXNavBarProps {
  title?: string;                // Main title of the nav bar
  subtitle?: string;             // Subtitle of the nav bar
  customTitle?: ReactNode;       // Custom title area
  leading?: ReactNode;           // Custom leading action area
  trailing?: ReactNode;          // Custom trailing action area
  showSeparator?: boolean;       // Whether to show separator below the nav bar (default: false)
  backgroundColor?: string;      // Background color
  zIndex?: number;               // Z-index (default: 1000)
  fixed?: boolean;               // Whether position is fixed (default: false)
  showTopSafeArea?: boolean;     // Whether to include top safe area (default: false)
  topSafeAreaHeight?: string;    // Custom height of top safe area
  showPlaceHolder?: boolean;     // Whether to include a placeholder (default: false)
  backgroundOpacity?: number;    // Opacity of background color
  titleOpacity?: number;         // Opacity of title
  heightPreset?: 52 | 44;        // Preset height (default: 52)
}

interface TUXNavBarIconActionProps {
  icon: ReactNode;               // Icon displayed in the action button
  opacity?: number;              // Opacity of the action button
  disabled?: boolean;            // Whether the button is disabled (default: false)
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void; // Click event handler
  testId?: string;               // Test ID
}
```

### Usage Examples

```tsx
// Basic usage
<TUXNavBar
  title="Page Title"
  leading={<TUXNavBarIconAction icon={<IconChevronLeftOffsetLTR />} onClick={handleBack} />}
  trailing={<TUXNavBarIconAction icon={<IconCheck />} onClick={handleDone} />}
/>

// With text actions
<TUXNavBar
  title="Page Title"
  leading={<button onClick={handleBack}>Cancel</button>}
  trailing={<button onClick={handleDone}>Done</button>}
/>

// With subtitle
<TUXNavBar
  title="Main Title"
  subtitle="Subtitle text"
  leading={<TUXNavBarIconAction icon={<IconChevronLeftOffsetLTR />} onClick={handleBack} />}
/>

// Fixed position with safe area
<TUXNavBar
  title="Fixed NavBar"
  fixed={true}
  showTopSafeArea={true}
  showPlaceHolder={true}
  showSeparator={true}
  backgroundColor="UIBackgroundPrimary"
/>
```

## Migration Notes

1. **Import Path Changes**:
   - Old: `import { TUXTitleBar, TUXAppBar, TUXNavBar } from "@byted-tiktok/tux-h5"`
   - New: `import { TUXNavBar, TUXNavBarIconAction } from "@byted-tiktok/tux-web/canary"`

2. **Component Consolidation**:
   - The new `TUXNavBar` replaces multiple old components: `TUXTitleBar`, `TUXAppBar`, and old `TUXNavBar`
   - Use the new `TUXNavBar` for all header/navigation bar needs

3. **Prop Changes**:
   - `leftText`/`rightText` → Use custom React elements in `leading`/`trailing` props
   - `leftIcon`/`rightIcon` → Use `TUXNavBarIconAction` in `leading`/`trailing` props
   - `onLeftClick`/`onRightClick` → Handle clicks in the components passed to `leading`/`trailing`

4. **Icon Changes**:
   - Old: `TUXIconChevronLeft` from `@byted-tiktok/tux-components` or `@byted-tiktok/tux-icons`
   - New: `IconChevronLeftOffsetLTR` from `@byted-tiktok/tux-icons` (note the naming change: no "TUXIcon" prefix)

5. **Additional Features in New Component**:
   - `subtitle`: Add a subtitle below the main title
   - `customTitle`: Use a completely custom title area
   - `fixed`: Make the navbar fixed at the top
   - `showTopSafeArea`: Add safe area for mobile devices
   - `showSeparator`: Add a separator line below the navbar
   - `heightPreset`: Choose between different height presets

6. **TUXNavBarIconAction**:
   - Use this component for icon buttons in the navbar
   - Pass the icon as a prop: `icon={<IconName />}`
   - Handle clicks with the `onClick` prop

7. **Styling Considerations**:
   - Use appropriate background colors (e.g., "UIBackgroundPrimary", "UISheetFlat1")
   - Consider using `fixed={true}` and `showPlaceHolder={true}` for fixed headers
   - For mobile applications, use `showTopSafeArea={true}` to respect device notches

8. **Integration with TUXSheet**:
   - When used inside `TUXSheet`, the `TUXNavBar` serves as the header
   - Set appropriate background color to match the sheet (e.g., "UISheetFlat1")