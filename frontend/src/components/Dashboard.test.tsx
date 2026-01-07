import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from './Dashboard';

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => { store[key] = value.toString(); },
        clear: () => { store = {}; }
    };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Helper to render with Router
const renderWithRouter = (component: React.ReactNode) => {
    return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Dashboard Component', () => {
    const mockProjects = [
        {
            id: 1,
            name: "Alpha Project",
            description: "Test Description",
            meetings: [
                { id: 101, name: "Kickoff", platform: "zoom", started_at: "2023-01-01" }
            ]
        }
    ];

    const mockRepos = [
        { id: 1, name: "repo-1", full_name: "user/repo-1", html_url: "http://github.com/user/repo-1" }
    ];

    beforeEach(() => {
        localStorageMock.setItem('auth_token', 'test-token');
        vi.clearAllMocks();

        // Mock fetch for Projects and User Repos
        globalThis.fetch = vi.fn().mockImplementation((url) => {
            if (url.includes('/projects')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(mockProjects),
                });
            }
            if (url.includes('/user/repos')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(mockRepos),
                });
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        });
    });

    it('renders project list correctly', async () => {
        renderWithRouter(<Dashboard userId="1" />);

        // Wait for data load
        await waitFor(() => {
            expect(screen.getByText('Alpha Project')).toBeInTheDocument();
        });
        expect(screen.getByText('Test Description')).toBeInTheDocument();
        expect(screen.getByText('Kickoff')).toBeInTheDocument();
    });

    it('opens the Start Meeting modal and handles input', async () => {
        renderWithRouter(<Dashboard userId="1" />);
        await waitFor(() => screen.getByText('Alpha Project'));

        // Click Start New Meeting button
        const startBtns = screen.getAllByText('+ Start New Meeting');
        fireEvent.click(startBtns[0]);

        // Check Modal Title
        expect(screen.getByText('Start New Meeting')).toBeInTheDocument();

        // Simulate User Input
        const urlInput = screen.getByPlaceholderText('https://...');
        fireEvent.change(urlInput, { target: { value: 'https://zoom.us/j/123' } });

        const checkbox = screen.getByLabelText(/I have notified all participants/i);
        fireEvent.click(checkbox);

        // Check if button is enabled
        const submitBtn = screen.getByText('Start Meeting & Invite Bot');
        expect(submitBtn).not.toBeDisabled();
    });
});
