# shadcn Cheat Sheet For This Project

This file is the "baby steps" version.

If you forget what to do, just follow the steps in order.

---

## 1. What shadcn is

shadcn is not a magic website component that stays outside your app.

When you **add** a shadcn component:

1. shadcn creates a file inside your project
2. the file usually goes into `src/components/ui/`
3. you can open that file and edit it like your own code

So:

- `add` = create component file in your project
- `import` = bring it into your page
- `use` = write `<Button />`, `<Input />`, etc.

---

## 2. Your project setup

This project is using:

- Vite
- React
- Tailwind v4
- `radix-vega` shadcn style
- TypeScript component files in `src/components/ui/`
- CSS variables in `src/styles/global.css`
- alias imports like `@/components/ui/button`

Important file:

- `frontend/components.json`

That file tells shadcn where to put things.

---

## 3. Where to run commands

Run shadcn commands inside:

```bash
frontend
```

That means:

```bash
cd frontend
```

Then run the add command.

---

## 4. The basic pattern

This is the whole idea:

### Step A. Add component

```bash
npx shadcn@latest add button
```

### Step B. Import component

```jsx
import { Button } from '@/components/ui/button'
```

### Step C. Use component

```jsx
<Button>Click me</Button>
```

That is the loop:

1. add
2. import
3. use

---

## 5. When do I use `add`?

Use `add` when the file does **not** exist yet.

Example:

If you want a `textarea` and you do not have:

```bash
src/components/ui/textarea.tsx
```

then add it:

```bash
npx shadcn@latest add textarea
```

If the file already exists, you usually do **not** add it again.

You just import it and use it.

---

## 6. What you currently have

Right now your project is only using these UI components:

- `button.tsx`
- `card.tsx`
- `checkbox.tsx`
- `input.tsx`
- `label.tsx`

They live in:

```bash
frontend/src/components/ui/
```

Your current login page uses them already.

---

## 7. The easiest real example

Your current login page follows this idea:

```jsx
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
```

Then you use them:

```jsx
<Card>
  <CardHeader>
    <CardTitle>Login</CardTitle>
  </CardHeader>

  <CardContent>
    <Label htmlFor="username">Username</Label>
    <Input id="username" />
  </CardContent>

  <CardFooter>
    <Button>Submit</Button>
  </CardFooter>
</Card>
```

That is normal shadcn usage.

---

## 8. How to add a new component

Example: you want `textarea`

### Step 1. Go to frontend

```bash
cd frontend
```

### Step 2. Add it

```bash
npx shadcn@latest add textarea
```

### Step 3. shadcn creates the file

Usually here:

```bash
src/components/ui/textarea.tsx
```

### Step 4. Import it in your page

```jsx
import { Textarea } from '@/components/ui/textarea'
```

### Step 5. Use it

```jsx
<Textarea placeholder="Type here" />
```

That is it.

---

## 9. Add many components at once

You can do this:

```bash
npx shadcn@latest add button input card checkbox label
```

Good when starting a page fast.

---

## 10. How to know what import to write

Easy rule:

If the file is:

```bash
src/components/ui/button.tsx
```

the import is usually:

```jsx
import { Button } from '@/components/ui/button'
```

If the file is:

```bash
src/components/ui/input.tsx
```

the import is:

```jsx
import { Input } from '@/components/ui/input'
```

Same pattern almost every time.

---

## 11. How to know the component name

Usually:

- `button.tsx` -> `Button`
- `input.tsx` -> `Input`
- `checkbox.tsx` -> `Checkbox`
- `label.tsx` -> `Label`

Open the file and look at the export at the bottom if you are unsure.

Example:

```tsx
export { Button, buttonVariants }
```

That means you can import `Button`.

---

## 12. What if I want to change the style?

You have 2 common ways:

### Way 1. Change it where you use it

```jsx
<Button className="w-full">Submit</Button>
```

### Way 2. Change the component file itself

Example:

```bash
src/components/ui/button.tsx
```

If you edit that file, every place using `Button` can change.

---

## 13. What if I only want simple page styling?

Use:

```bash
src/styles/global.css
```

That is for theme colors, base styles, and app-wide styling.

Do **not** put component logic there.

Put page logic in `.jsx` or `.tsx` files.

---

## 14. How to build a simple form

This is the easy pattern:

```jsx
<div className="grid gap-2">
  <Label htmlFor="username">Username</Label>
  <Input id="username" type="text" />
</div>
```

For password:

```jsx
<div className="grid gap-2">
  <Label htmlFor="password">Password</Label>
  <Input id="password" type="password" />
</div>
```

For remember me:

```jsx
<div className="flex items-center gap-2">
  <Checkbox id="remember" />
  <Label htmlFor="remember">Remember me</Label>
</div>
```

For submit:

```jsx
<Button className="w-full">Submit</Button>
```

---

## 15. When do I use React state?

Use state when the value needs to change and React needs to remember it.

Example:

```jsx
const [rememberMe, setRememberMe] = useState(false)
```

Then:

```jsx
<Checkbox
  checked={rememberMe}
  onCheckedChange={(value) => setRememberMe(Boolean(value))}
/>
```

Simple meaning:

- `checked` = current value
- `onCheckedChange` = what to do when it changes

---

## 16. Most common commands

### Add one component

```bash
npx shadcn@latest add button
```

### Add many

```bash
npx shadcn@latest add button input card checkbox label
```

### Start dev server

```bash
npm run dev
```

### Lint project

```bash
npm run lint
```

### Build project

```bash
npm run build
```

---

## 17. Very common mistakes

### Mistake 1. You added component, but did not import it

Wrong:

```jsx
<Button>Save</Button>
```

without:

```jsx
import { Button } from '@/components/ui/button'
```

### Mistake 2. Wrong import path

Wrong:

```jsx
import { Button } from './button'
```

Usually in this project, use:

```jsx
import { Button } from '@/components/ui/button'
```

### Mistake 3. You are not inside `frontend`

If command fails, make sure you are in:

```bash
frontend
```

### Mistake 4. You are trying to use component that was deleted

If a file is gone from `src/components/ui/`, add it again first.

---

## 18. Super short memory trick

If you forget everything, remember this:

### "Add, import, use."

```bash
npx shadcn@latest add button
```

```jsx
import { Button } from '@/components/ui/button'
```

```jsx
<Button>Click</Button>
```

That is the main idea.

---

## 19. Where to check if stuck

- `frontend/components.json`
- `frontend/src/components/ui/`
- `frontend/src/pages/`
- `frontend/src/styles/global.css`

If confused:

1. check whether the component file exists
2. check whether you imported it
3. check whether you used the correct component name
4. run `npm run lint`

---

## 20. Good starter packs

### For login page

```bash
npx shadcn@latest add button input card checkbox label
```

### For simple form page

```bash
npx shadcn@latest add button input label textarea select checkbox
```

### For modal page

```bash
npx shadcn@latest add button dialog
```

---

## 21. Final simple rule

shadcn is easiest if you think like this:

- command makes file
- file is yours
- import file
- use component
- style with Tailwind classes

That is all.
