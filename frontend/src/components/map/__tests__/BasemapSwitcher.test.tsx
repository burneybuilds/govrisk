import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BasemapSwitcher, type BasemapSwitcherProps } from '../BasemapSwitcher';
import type { BasemapId } from '../../../types/map';
import { I18nProvider } from '../../../i18n';

function renderSwitcher(basemap: BasemapId = 'street') {
  const props: BasemapSwitcherProps = { basemap, onChange: vi.fn() };
  const view = render(
    <I18nProvider>
      <BasemapSwitcher {...props} />
    </I18nProvider>,
  );
  return { view, handlers: props };
}

describe('BasemapSwitcher', () => {
  it('exposes exactly two basemap options as a radiogroup', () => {
    renderSwitcher();
    expect(screen.getByRole('radiogroup', { name: /basemap/i })).toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(2);
  });

  it('marks the active basemap as the checked radio', () => {
    renderSwitcher();
    expect(screen.getByRole('radio', { name: /street/i })).toBeChecked();
    expect(screen.getByRole('radio', { name: /satellite/i })).not.toBeChecked();
  });

  it('switches to the satellite basemap', async () => {
    const user = userEvent.setup();
    const { handlers } = renderSwitcher();
    await user.click(screen.getByRole('radio', { name: /satellite/i }));
    expect(handlers.onChange).toHaveBeenCalledWith('satellite');
  });

  it('switches back to the street basemap', async () => {
    const user = userEvent.setup();
    const { handlers } = renderSwitcher('satellite');
    expect(screen.getByRole('radio', { name: /satellite/i })).toBeChecked();
    await user.click(screen.getByRole('radio', { name: /street/i }));
    expect(handlers.onChange).toHaveBeenCalledWith('street');
  });
});
