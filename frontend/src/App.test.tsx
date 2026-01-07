import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
            store[key] = value.toString();
        },
        removeItem: (key: string) => {
            delete store[key];
        },
        clear: () => {
            store = {};
        }
    };
})();

Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
});

describe('App Authentication Flow', () => {
    beforeEach(() => {
        localStorageMock.clear();
        vi.clearAllMocks();
        // Default to root url
        window.history.pushState({}, 'Test page', '/');
    });

    it('redirects to login when unauthenticated', async () => {
        render(<App />);

        // Should NOT see Dashboard content
        expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();

        // Should see Login content (from Login.tsx)
        // We look for the specific button text "Sign in with GitHub"
        expect(screen.getByText('Sign in with GitHub')).toBeInTheDocument();
    });

    it('renders Dashboard when authenticated', async () => {
        // Setup authenticated state
        localStorageMock.setItem('auth_token', 'fake-jwt-token');
        localStorageMock.setItem('voice_spec_user_id', 'test-user-123');

        render(<App />);

        // Should see Dashboard elements
        // Use getByRole to be specific (Dashboard appears in Nav and as H2)
        expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
        expect(screen.getByText('User: test-user-123')).toBeInTheDocument();
        expect(screen.queryByText('Sign in with GitHub')).not.toBeInTheDocument();
    });

    it('logs out and redirects to login', async () => {
        // Start authenticated
        localStorageMock.setItem('auth_token', 'fake-jwt-token');
        localStorageMock.setItem('voice_spec_user_id', 'test-user-123');

        render(<App />);

        // Verify we are logged in
        expect(screen.getByText('User: test-user-123')).toBeInTheDocument();

        // Find and click Logout
        const logoutBtn = screen.getByText('Logout');
        fireEvent.click(logoutBtn);

        // Should remove item from localStorage
        await waitFor(() => {
            expect(screen.queryByText('User: test-user-123')).not.toBeInTheDocument();
        });

        // Should be back at login
        expect(screen.getByText('Sign in with GitHub')).toBeInTheDocument();

        // Check localStorage was cleared of keys (specific ones)
        expect(localStorageMock.getItem('auth_token')).toBeNull();
        expect(localStorageMock.getItem('voice_spec_user_id')).toBeNull();
    });
});
