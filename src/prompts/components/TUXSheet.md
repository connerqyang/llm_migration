# TUXSheet Migration Guide

## Old TUXSheetWIP Component

### Import Example

```tsx
import { TUXSheetWIP } from "@byted-tiktok/tux-h5";
```

### Props Interface

```tsx
interface TUXSheetWIPProps {
  isVisible?: boolean;         // Controls visibility of the sheet (default: false)
  size?: "large" | "medium";   // Size of the sheet (default: "medium")
  minHeight?: string | number; // Minimum height (default: 240)
  height?: string | number;    // Height of the sheet
  maxHeight?: string | number; // Maximum height of the sheet
  onDismiss?: () => void;      // Callback when sheet is dismissed
  getContainer?: false | GetContainerFn; // Custom container for the sheet
  hasOverlay?: boolean;        // Whether to show overlay (default: true)
  backgroundColor?: string;    // Background color of the sheet (default: "BGSecondary")
  header?: ReactNode;          // Custom header component, typically TUXTitleBar
}
```

### Usage Examples

```tsx
// Example without title bar
<TUXSheetWIP 
  isVisible={isVisible} 
  onDismiss={() => setIsVisible(false)}
>
  <div>Content goes here</div>
  <TUXButton text="Close" onClick={() => setIsVisible(false)} />
</TUXSheetWIP>

// Example with TUXTitleBar
<TUXSheetWIP 
  isVisible={isVisible} 
  onDismiss={() => setIsVisible(false)}
  header={
    <TUXTitleBar
      title="Sheet Title"
      onLeftClick={() => setIsVisible(false)}
      rightText="Done"
      onRightClick={handleDone}
    />
  }
>
  <div>Content goes here</div>
</TUXSheetWIP>
```

## New TUXSheet Component

### Import Example

```tsx
import { TUXSheet } from "@byted-tiktok/tux-web/canary";
import { TUXNavBar, TUXNavBarIconAction } from "@byted-tiktok/tux-web/canary";
import { IconChevronLeftOffsetLTR, IconXMarkSmall } from "@byted-tiktok/tux-icons";
```

### Props Interface

```tsx
interface TUXSheetProps {
  position?: "bottom" | "left" | "right" | "top"; // Position of the sheet (default: "bottom")
  heightModePreset?: "auto" | "full" | "half" | "third"; // Preset height mode (default: "auto")
  closeOnOutsideClick?: boolean; // Whether to close when clicking outside (default: true)
  height?: string; // Custom height of the sheet
  minHeight?: string; // Minimum height of the sheet
  maxHeight?: string; // Maximum height of the sheet
  width?: string; // Custom width of the sheet
  minWidth?: string; // Minimum width of the sheet
  maxWidth?: string; // Maximum width of the sheet
  marginBottom?: string; // Bottom margin of the sheet
  zIndex?: number; // Z-index of the sheet (default: 2200)
  overlayBackgroundColor?: string; // Background color of the overlay
  sheetBackgroundColor?: string; // Background color of the sheet
  visible?: boolean; // Controls visibility of the sheet (default: false)
  onVisibleChange?: (visible: boolean) => void; // Callback when visibility changes
  autoFocus?: boolean; // Whether to auto focus the sheet (default: false)
  root?: HTMLElement; // Custom root element
  shouldCloseOnOutsideClick?: (e: MouseEvent) => boolean; // Custom logic for closing on outside click
  testId?: string; // Test ID for testing
}
```

### Usage Examples

```tsx
// Basic usage with TUXNavBar
const [visible, setVisible] = useState(false);

<TUXSheet visible={visible} onVisibleChange={setVisible}>
  <TUXNavBar
    title="Sheet Title"
    leading={<TUXNavBarIconAction icon={<IconChevronLeftOffsetLTR />} onClick={() => setVisible(false)} />}
    trailing={<TUXNavBarIconAction icon={<IconXMarkSmall />} onClick={() => setVisible(false)} />}
    backgroundColor="UISheetFlat1"
  />
  <div style={{ padding: 16 }}>
    <TUXButton text="Close" onClick={() => setVisible(false)} />
  </div>
  <div style={{ flex: '1 1 0%', paddingInline: 16, paddingBlock: 8, overflowY: 'auto' }}>
    Content goes here
  </div>
</TUXSheet>

// With position control (for desktop)
<TUXSheet 
  visible={visible} 
  onVisibleChange={setVisible} 
  position="left"
>
  <TUXNavBar
    title="Side Sheet"
    leading={<TUXNavBarIconAction icon={<IconXMarkSmall />} onClick={() => setVisible(false)} />}
    backgroundColor="UISheetFlat1"
  />
  <div style={{ padding: 16 }}>
    Content goes here
  </div>
</TUXSheet>
```

## Migration Notes

1. **Import Path Changes**:
   - Old: `import { TUXSheetWIP } from "@byted-tiktok/tux-h5"`
   - New: `import { TUXSheet } from "@byted-tiktok/tux-web/canary"`

2. **Component Name Change**:
   - Old: `TUXSheetWIP`
   - New: `TUXSheet`

3. **Prop Changes**:
   - `isVisible` → `visible`
   - `onDismiss` → `onVisibleChange`
   - `header` → No direct equivalent; use `TUXNavBar` as a child component instead
   - `backgroundColor` → `sheetBackgroundColor`
   - `size` → Use `heightModePreset` for similar functionality

4. **Header/Navigation Changes**:
   - Old: Used `header` prop with `TUXTitleBar`
   - New: Add `TUXNavBar` as a child component inside `TUXSheet`
   - Import `TUXNavBarIconAction` for navigation actions
   - Import icons from `@byted-tiktok/tux-icons` (note the naming change: no "TUXIcon" prefix)

5. **Additional Props in New Component**:
   - `position`: Controls where the sheet appears from ("bottom", "left", "right", "top")
   - `heightModePreset`: Preset height modes
   - `closeOnOutsideClick`: Whether to close when clicking outside
   - `width`, `minWidth`, `maxWidth`: Width control options
   - `marginBottom`: Bottom margin
   - `zIndex`: Z-index of the sheet
   - `overlayBackgroundColor`: Background color of the overlay
   - `autoFocus`: Whether to auto-focus the sheet
   - `root`: Custom root element
   - `testId`: Test ID for testing

6. **Important Usage Notes**:
   - Do not use conditional rendering like `visible && <TUXSheet visible={visible} />` as it will cause unexpected behavior
   - TUXSheet uses lazy creation mode internally
   - TUXSheet only provides the container and basic interactions; use other components like TUXNavBar for content structure

7. **Styling Considerations**:
   - Content should be structured with appropriate flex and padding styles
   - For scrollable content, use `flex: '1 1 0%'` and `overflowY: 'auto'`

8. **TUXNavBar Integration**:
   - Use `leading` and `trailing` props to add navigation actions
   - Set appropriate `backgroundColor` for the navbar (e.g., "UISheetFlat1")
   - Use `TUXNavBarIconAction` with icons for navigation buttons