import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Button from './Button.svelte';

describe('Button', () => {
  const child = (text) => () => text;

  it('renders with default primary variant', () => {
    render(Button, { children: child('Click Me') });
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
    expect(button.className).toContain('button-primary');
  });

  it('renders as disabled when disabled prop is true', () => {
    render(Button, { children: child('Disabled'), disabled: true });
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('applies secondary variant class', () => {
    render(Button, { children: child('Secondary'), variant: 'secondary' });
    const button = screen.getByRole('button');
    expect(button.className).toContain('button-secondary');
  });

  it('applies danger variant class', () => {
    render(Button, { children: child('Danger'), variant: 'danger' });
    const button = screen.getByRole('button');
    expect(button.className).toContain('button-danger');
  });

  it('renders with correct type attribute', () => {
    render(Button, { children: child('Submit'), type: 'submit' });
    const button = screen.getByRole('button');
    expect(button.type).toBe('submit');
  });
});
