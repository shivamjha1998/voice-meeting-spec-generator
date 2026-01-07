import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import MeetingMonitor from './MeetingMonitor';

describe('MeetingMonitor Component', () => {
    // Use unknown or specific function types to avoid 'any'
    let mockWs: {
        close: ReturnType<typeof vi.fn>;
        send: ReturnType<typeof vi.fn>;
        readyState: number;
        onopen?: (event: unknown) => void;
        onmessage?: (event: { data: string }) => void;
        onerror?: (event: unknown) => void;
        onclose?: (event: unknown) => void;
    };

    beforeEach(() => {
        // Mock Fetch for initial transcripts
        globalThis.fetch = vi.fn().mockResolvedValue({
            json: () => Promise.resolve([
                { id: 1, speaker: "Alice", text: "Hello world", timestamp: Date.now() }
            ]),
        });

        // Mock WebSocket
        mockWs = {
            close: vi.fn(),
            send: vi.fn(),
            readyState: 1
        };

        // Intercept WebSocket constructor
        globalThis.WebSocket = vi.fn(function () {
            return mockWs;
        }) as unknown as typeof WebSocket;
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders initial transcripts fetched from API', async () => {
        render(<MeetingMonitor meetingId={1} />);

        await waitFor(() => {
            expect(screen.getByText('Hello world')).toBeInTheDocument();
            expect(screen.getByText('Alice')).toBeInTheDocument();
        });
    });

    it('receives real-time updates via WebSocket', async () => {
        render(<MeetingMonitor meetingId={1} />);

        // Simulate WebSocket open
        mockWs.onopen?.({} as unknown);

        // Simulate incoming message
        const wsMessage = {
            speaker: "Bob",
            text: "This is a live update",
            timestamp: Date.now()
        };

        // Trigger the message event handler directly
        await waitFor(() => expect(mockWs.onmessage).toBeDefined());

        // Fire the event
        mockWs.onmessage?.({ data: JSON.stringify(wsMessage) });

        await waitFor(() => {
            expect(screen.getByText('This is a live update')).toBeInTheDocument();
            expect(screen.getByText('Bob')).toBeInTheDocument();
        });
    });

    it('handles the "Summon Bot" action', async () => {
        render(<MeetingMonitor meetingId={1} />);

        // Mock the specific join endpoint
        const joinMock = vi.fn().mockResolvedValue({ json: () => ({ status: "queued" }) });
        globalThis.fetch = vi.fn().mockImplementation((url) => {
            if (url.includes('/join')) return joinMock();
            return Promise.resolve({ json: () => [] }); // default for transcripts
        });

        const summonBtn = screen.getByText('Summon Bot');
        fireEvent.click(summonBtn);

        await waitFor(() => {
            expect(joinMock).toHaveBeenCalled();
        });
    });
});
