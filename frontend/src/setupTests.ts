import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock scrollIntoView for JSDOM
Element.prototype.scrollIntoView = vi.fn();
