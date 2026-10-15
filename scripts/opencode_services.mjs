// Fixtures for external services; the Permission layer body remains source-owned.
import { Context, Effect } from 'effect';
import { Agent as AgentSchema } from './schema/agent.ts';
const tag = name => class extends Context.Service()(name) {};
export const Bus={Service:tag('probe/Bus')};
export const Location={Service:tag('probe/Location')};
export const Agent={Service:tag('probe/Agent'),ID:AgentSchema.ID};
export const SessionStore={Service:tag('probe/SessionStore')};
export const PermissionSaved={Service:tag('probe/PermissionSaved')};
export const PluginHooks={Service:tag('probe/PluginHooks')};
// Capture the unchanged Layer rather than booting the application's dependency graph.
export const makeLocationNode = input => input;
