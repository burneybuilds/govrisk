import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LayerControlPanel, type LayerControlPanelProps } from '../LayerControlPanel';
import type { LayerDataStatus } from '../LayerControlPanel';
import type { MapLayerState } from '../../../types/map';

function makeState(): MapLayerState {
  return {
    choropleth: 'risk',
    riskMarkers: true,
    projects: true,
    weatherOverlay: true,
    riskOpacity: 0.85,
    disasterOpacity: 0.85,
    weatherOpacity: 0.6,
  };
}

function makeStatus(): LayerDataStatus {
  return {
    risk: { isLoading: false, isError: false },
    disaster: { isLoading: false, isError: false },
    weather: { isLoading: false, isError: false },
    projects: { isLoading: false, isError: false },
  };
}

function renderPanel(status: LayerDataStatus = makeStatus(), state: MapLayerState = makeState()) {
  const handlers = {
    onSetChoropleth: vi.fn(),
    onClearChoropleth: vi.fn(),
    onToggleRiskMarkers: vi.fn(),
    onToggleProjects: vi.fn(),
    onToggleWeatherOverlay: vi.fn(),
    onSetOpacity: vi.fn(),
  } as const;
  const props: LayerControlPanelProps = {
    layerState: state,
    dataStatus: status,
    ...handlers,
  };
  const view = render(<LayerControlPanel {...props} />);
  return { view, handlers };
}

describe('LayerControlPanel', () => {
  it('renders the Layers toggle with accessible label', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /layers/i })).toBeInTheDocument();
  });

  it('shows risk choropleth as active when choropleth === risk', () => {
    renderPanel();
    expect(screen.getByRole('checkbox', { name: /risk score/i })).toBeChecked();
  });

  it('enforces single-choropleth: checking disaster calls setChoropleth for disaster', async () => {
    const user = userEvent.setup();
    const { handlers } = renderPanel();
    await user.click(screen.getByRole('checkbox', { name: /disaster history/i }));
    expect(handlers.onSetChoropleth).toHaveBeenCalledWith('disaster');
  });

  it('unchecking the active choropleth clears it', async () => {
    const user = userEvent.setup();
    const { handlers } = renderPanel();
    await user.click(screen.getByRole('checkbox', { name: /risk score/i }));
    expect(handlers.onClearChoropleth).toHaveBeenCalledTimes(1);
  });

  it('toggles weather overlay independently', async () => {
    const user = userEvent.setup();
    const { handlers } = renderPanel();
    await user.click(screen.getByRole('checkbox', { name: /weather overlay/i }));
    expect(handlers.onToggleWeatherOverlay).toHaveBeenCalledTimes(1);
  });

  it('toggles the infrastructure projects layer', async () => {
    const user = userEvent.setup();
    const { handlers } = renderPanel();
    await user.click(screen.getByRole('checkbox', { name: /infrastructure projects/i }));
    expect(handlers.onToggleProjects).toHaveBeenCalledTimes(1);
  });

  it('emits opacity changes for the active layer', () => {
    const { handlers } = renderPanel();
    fireEvent.change(screen.getByRole('slider', { name: /risk choropleth opacity/i }), {
      target: { value: '0.5' },
    });
    expect(handlers.onSetOpacity).toHaveBeenCalledWith('risk', 0.5);
  });

  it('flags failed layers without blocking healthy ones', () => {
    const status = makeStatus();
    status.disaster.isError = true;
    renderPanel(status);
    expect(screen.getAllByLabelText('Source unavailable').length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText('Ready').length).toBeGreaterThan(0);
  });
});
