/** Fixture dependency ports only. Permission logic and Effect runtime are NOT mocked. */
import {Context,Schema} from 'effect';
export const makeLocationNode=value=>value;
export const Bus={Service:class extends Context.Service()('@qa/Bus'){},node:{}};
export const Location={Service:class extends Context.Service()('@qa/Location'){},node:{}};
export const Agent={ID:Schema.String,Service:class extends Context.Service()('@qa/Agent'){},node:{}};
export const SessionStore={Service:class extends Context.Service()('@qa/SessionStore'){},node:{}};
export const SessionSchema={ID:Schema.String};
export const SessionErrors={NotFoundError:class extends Schema.TaggedError()('Session.NotFoundError',{sessionID:Schema.String}){}};
export const PermissionSaved={Service:class extends Context.Service()('@qa/PermissionSaved'){},node:{}};
export const PluginHooks={Service:class extends Context.Service()('@qa/PluginHooks'){},node:{}};
