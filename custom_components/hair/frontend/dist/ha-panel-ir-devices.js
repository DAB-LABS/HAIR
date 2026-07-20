function e(e,t,i,a){var r,o=arguments.length,n=o<3?t:null===a?a=Object.getOwnPropertyDescriptor(t,i):a;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(e,t,i,a);else for(var s=e.length-1;s>=0;s--)(r=e[s])&&(n=(o<3?r(n):o>3?r(t,i,n):r(t,i))||n);return o>3&&n&&Object.defineProperty(t,i,n),n}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,a=Symbol(),r=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==a)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=r.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(t,e))}return e}toString(){return this.cssText}};const n=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,a)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[a+1],e[0]);return new o(i,e,a)},s=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,a))(t)})(e):e,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:p,getOwnPropertySymbols:g,getPrototypeOf:m}=Object,u=globalThis,h=u.trustedTypes,_=h?h.emptyScript:"",v=u.reactiveElementPolyfillSupport,b=(e,t)=>e,f={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),w={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:y};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let k=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=w){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),a=this.getPropertyDescriptor(e,i,t);void 0!==a&&d(this.prototype,e,a)}}static getPropertyDescriptor(e,t,i){const{get:a,set:r}=c(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:a,set(t){const o=a?.call(this);r?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??w}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const e=m(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const e=this.properties,t=[...p(e),...g(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(s(e))}else void 0!==e&&t.push(s(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,a)=>{if(i)e.adoptedStyleSheets=a.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of a){const a=document.createElement("style"),r=t.litNonce;void 0!==r&&a.setAttribute("nonce",r),a.textContent=i.cssText,e.appendChild(a)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),a=this.constructor._$Eu(e,i);if(void 0!==a&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:f).toAttribute(t,i.type);this._$Em=e,null==r?this.removeAttribute(a):this.setAttribute(a,r),this._$Em=null}}_$AK(e,t){const i=this.constructor,a=i._$Eh.get(e);if(void 0!==a&&this._$Em!==a){const e=i.getPropertyOptions(a),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:f;this._$Em=a;const o=r.fromAttribute(t,e.type);this[a]=o??this._$Ej?.get(a)??o,this._$Em=null}}requestUpdate(e,t,i,a=!1,r){if(void 0!==e){const o=this.constructor;if(!1===a&&(r=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??y)(r,t)||i.useDefault&&i.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:a,wrapped:r},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==r||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===a&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,a=this[t];!0!==e||this._$AL.has(t)||void 0===a||this.C(t,void 0,i,a)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};k.elementStyles=[],k.shadowRootOptions={mode:"open"},k[b("elementProperties")]=new Map,k[b("finalized")]=new Map,v?.({ReactiveElement:k}),(u.reactiveElementVersions??=[]).push("2.1.2");const x=globalThis,$=e=>e,S=x.trustedTypes,C=S?S.createPolicy("lit-html",{createHTML:e=>e}):void 0,A="$lit$",z=`lit$${Math.random().toFixed(9).slice(2)}$`,D="?"+z,E=`<${D}>`,I=document,T=()=>I.createComment(""),R=e=>null===e||"object"!=typeof e&&"function"!=typeof e,P=Array.isArray,H="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,M=/-->/g,j=/>/g,L=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),V=/'/g,q=/"/g,O=/^(?:script|style|textarea|title)$/i,B=(e,...t)=>({_$litType$:1,strings:e,values:t}),U=Symbol.for("lit-noChange"),F=Symbol.for("lit-nothing"),W=new WeakMap,G=I.createTreeWalker(I,129);function Z(e,t){if(!P(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==C?C.createHTML(t):t}class K{constructor({strings:e,_$litType$:t},i){let a;this.parts=[];let r=0,o=0;const n=e.length-1,s=this.parts,[l,d]=((e,t)=>{const i=e.length-1,a=[];let r,o=2===t?"<svg>":3===t?"<math>":"",n=N;for(let t=0;t<i;t++){const i=e[t];let s,l,d=-1,c=0;for(;c<i.length&&(n.lastIndex=c,l=n.exec(i),null!==l);)c=n.lastIndex,n===N?"!--"===l[1]?n=M:void 0!==l[1]?n=j:void 0!==l[2]?(O.test(l[2])&&(r=RegExp("</"+l[2],"g")),n=L):void 0!==l[3]&&(n=L):n===L?">"===l[0]?(n=r??N,d=-1):void 0===l[1]?d=-2:(d=n.lastIndex-l[2].length,s=l[1],n=void 0===l[3]?L:'"'===l[3]?q:V):n===q||n===V?n=L:n===M||n===j?n=N:(n=L,r=void 0);const p=n===L&&e[t+1].startsWith("/>")?" ":"";o+=n===N?i+E:d>=0?(a.push(s),i.slice(0,d)+A+i.slice(d)+z+p):i+z+(-2===d?t:p)}return[Z(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),a]})(e,t);if(this.el=K.createElement(l,i),G.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(a=G.nextNode())&&s.length<n;){if(1===a.nodeType){if(a.hasAttributes())for(const e of a.getAttributeNames())if(e.endsWith(A)){const t=d[o++],i=a.getAttribute(e).split(z),n=/([.?@])?(.*)/.exec(t);s.push({type:1,index:r,name:n[2],strings:i,ctor:"."===n[1]?ee:"?"===n[1]?te:"@"===n[1]?ie:J}),a.removeAttribute(e)}else e.startsWith(z)&&(s.push({type:6,index:r}),a.removeAttribute(e));if(O.test(a.tagName)){const e=a.textContent.split(z),t=e.length-1;if(t>0){a.textContent=S?S.emptyScript:"";for(let i=0;i<t;i++)a.append(e[i],T()),G.nextNode(),s.push({type:2,index:++r});a.append(e[t],T())}}}else if(8===a.nodeType)if(a.data===D)s.push({type:2,index:r});else{let e=-1;for(;-1!==(e=a.data.indexOf(z,e+1));)s.push({type:7,index:r}),e+=z.length-1}r++}}static createElement(e,t){const i=I.createElement("template");return i.innerHTML=e,i}}function X(e,t,i=e,a){if(t===U)return t;let r=void 0!==a?i._$Co?.[a]:i._$Cl;const o=R(t)?void 0:t._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(e),r._$AT(e,i,a)),void 0!==a?(i._$Co??=[])[a]=r:i._$Cl=r),void 0!==r&&(t=X(e,r._$AS(e,t.values),r,a)),t}class Y{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,a=(e?.creationScope??I).importNode(t,!0);G.currentNode=a;let r=G.nextNode(),o=0,n=0,s=i[0];for(;void 0!==s;){if(o===s.index){let t;2===s.type?t=new Q(r,r.nextSibling,this,e):1===s.type?t=new s.ctor(r,s.name,s.strings,this,e):6===s.type&&(t=new ae(r,this,e)),this._$AV.push(t),s=i[++n]}o!==s?.index&&(r=G.nextNode(),o++)}return G.currentNode=I,a}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,a){this.type=2,this._$AH=F,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=a,this._$Cv=a?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=X(this,e,t),R(e)?e===F||null==e||""===e?(this._$AH!==F&&this._$AR(),this._$AH=F):e!==this._$AH&&e!==U&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>P(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==F&&R(this._$AH)?this._$AA.nextSibling.data=e:this.T(I.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,a="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=K.createElement(Z(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===a)this._$AH.p(t);else{const e=new Y(a,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=W.get(e.strings);return void 0===t&&W.set(e.strings,t=new K(e)),t}k(e){P(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,a=0;for(const r of e)a===t.length?t.push(i=new Q(this.O(T()),this.O(T()),this,this.options)):i=t[a],i._$AI(r),a++;a<t.length&&(this._$AR(i&&i._$AB.nextSibling,a),t.length=a)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=$(e).nextSibling;$(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class J{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,a,r){this.type=1,this._$AH=F,this._$AN=void 0,this.element=e,this.name=t,this._$AM=a,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=F}_$AI(e,t=this,i,a){const r=this.strings;let o=!1;if(void 0===r)e=X(this,e,t,0),o=!R(e)||e!==this._$AH&&e!==U,o&&(this._$AH=e);else{const a=e;let n,s;for(e=r[0],n=0;n<r.length-1;n++)s=X(this,a[i+n],t,n),s===U&&(s=this._$AH[n]),o||=!R(s)||s!==this._$AH[n],s===F?e=F:e!==F&&(e+=(s??"")+r[n+1]),this._$AH[n]=s}o&&!a&&this.j(e)}j(e){e===F?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends J{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===F?void 0:e}}class te extends J{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==F)}}class ie extends J{constructor(e,t,i,a,r){super(e,t,i,a,r),this.type=5}_$AI(e,t=this){if((e=X(this,e,t,0)??F)===U)return;const i=this._$AH,a=e===F&&i!==F||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,r=e!==F&&(i===F||a);a&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ae{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){X(this,e)}}const re={I:Q},oe=x.litHtmlPolyfillSupport;oe?.(K,Q),(x.litHtmlVersions??=[]).push("3.3.3");const ne=globalThis;let se=class extends k{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const a=i?.renderBefore??t;let r=a._$litPart$;if(void 0===r){const e=i?.renderBefore??null;a._$litPart$=r=new Q(t.insertBefore(T(),e),e,void 0,i??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return U}};se._$litElement$=!0,se.finalized=!0,ne.litElementHydrateSupport?.({LitElement:se});const le=ne.litElementPolyfillSupport;le?.({LitElement:se}),(ne.litElementVersions??=[]).push("4.2.2");const de={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:y},ce=(e=de,t,i)=>{const{kind:a,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===a&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===a){const{name:a}=i;return{set(i){const r=t.get.call(this);t.set.call(this,i),this.requestUpdate(a,r,e,!0,i)},init(t){return void 0!==t&&this.C(a,void 0,e,t),t}}}if("setter"===a){const{name:a}=i;return function(i){const r=this[a];t.call(this,i),this.requestUpdate(a,r,e,!0,i)}}throw Error("Unsupported decorator location: "+a)};function pe(e){return(t,i)=>"object"==typeof i?ce(e,t,i):((e,t,i)=>{const a=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),a?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function ge(e){return pe({...e,state:!0,attribute:!1})}const me=e=>e,ue=e=>customElements.get(e)?me:(e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)})(e);class he{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}duplicateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/duplicate",device_id:e,new_name:t})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}setCommandTxForceRaw(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/command/set-tx-force-raw",device_id:e,command_id:t,tx_force_raw:i})}reorderCommands(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/reorder-commands",device_id:e,command_ids:t})}reorderDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/devices/reorder",device_ids:e})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}listReceivers(){return this.hass.connection.sendMessagePromise({type:"hair/receivers"})}getSnifferStatus(){return this.hass.connection.sendMessagePromise({type:"hair/sniffer/status"})}getCodeBrands(){return this.hass.connection.sendMessagePromise({type:"hair/codes/brands"})}importCodeRemote(e,t){const i={type:"hair/codes/import-remote",codebook_id:e};return t&&(i.name=t),this.hass.connection.sendMessagePromise(i)}async startCapture(e,t,i){let a=null;const r=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(a=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===a)throw new Error("Capture session did not start");return{session:a,unsubscribe:r}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getActionOptions(e){return this.hass.connection.sendMessagePromise({type:"hair/device/action-options",device_type:e})}updateMapping(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/device/update-mapping",device_id:e,command_name:t,action_key:i})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_id:t})}testSignal(e,t){const i={type:"hair/unknown/test",signal_id:e};return t&&(i.emitter_entity_id=t),this.hass.connection.sendMessagePromise(i)}renameUnknown(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/rename",device_id:e,label:t})}clearUnknowns(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear",...e?{source:e}:{}})}setSignalAlias(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/set-alias",device_id:e,signal_id:t,alias:i})}reorderUnknownDevices(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/reorder",source:e,device_ids:t})}reorderUnknownSignals(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/reorder",device_id:e,signal_ids:t})}createRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-remote",name:e})}createSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-signal",...e})}editSignalPronto(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/edit-pronto",...e})}validatePronto(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/validate-pronto",pronto:e})}snapPreview(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/snap-preview",...e})}updateCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/command/update",...e})}deleteRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/delete-remote",device_id:e})}listPluckVendors(){return this.hass.connection.sendMessagePromise({type:"hair/pluck/list-vendors"})}runPluck(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/run",...e})}createPluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-blaster",...e})}createPluckedSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-signal",...e})}deletePluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/delete-blaster",device_id:e})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}async subscribeSignalUpdated(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_updated")}async subscribeDismissActivity(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_dismiss_activity")}listTriggers(){return this.hass.connection.sendMessagePromise({type:"hair/triggers"})}createTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/create",...e})}updateTrigger(e,t){return this.hass.connection.sendMessagePromise({type:"hair/trigger/update",trigger_id:e,...t})}deleteTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/delete",trigger_id:e})}async subscribeTriggerFired(e){return this.hass.connection.subscribeMessage(e,{type:"hair/trigger/subscribe"})}}var _e={"_meta.review":"source","panel.loading":"Loading…","panel.load_failed":"Failed to load devices: {message}","panel.open_menu":"Open menu","panel.tab.devices":"Devices","panel.tagline.devices":"Manage your IR devices and the hardware that drives them.","panel.tagline.sniffer":"Capture IR codes live from the air.","panel.tagline.clips":"Build remotes by pasting known IR codes.","panel.tagline.plucker":"Pluck IR codes from existing blasters.","panel.tagline.mirror":"See your live Home Assistant infrared transmissions.","common.confirm":"Confirm","common.cancel":"Cancel","common.are_you_sure":"Are you sure?","common.remove":"Remove","alias.placeholder":"Alias for this signal","alias.tag":"alias","alias.clear":"Clear alias","alias.edit":"Click to edit alias","alias.name":"Click to name this signal","picker.emitters_label":"IR emitters","picker.add_emitter":"+ Add emitter...","picker.no_emitters":"No IR emitters found.","picker.all_emitters_selected":"All emitters selected.","picker.receivers_label":"Via receiver(s):","picker.add_receiver":"+ Add receiver...","picker.no_receivers":"No IR receivers found.","picker.all_receivers_selected":"All receivers selected.","device_type.media_player":"Media Player","device_type.ac":"Air Conditioner","device_type.fan":"Fan","device_type.light":"Light","device_type.switch":"Switch","device_type.screen":"Screen / Shade","device_type.other":"Other","common.name":"Name","common.device_type":"Device type","common.name_required":"Name is required.","common.creating":"Creating...","common.device_name_placeholder":"e.g. Living Room TV","promote.heading":"Promote to Device","promote.device_name":"Device name","promote.device_name_required":"Device name is required.","promote.emitter_required":"Select at least one IR emitter.","promote.create_device":"Create Device","adddev.heading":"Add Device","adddev.emitter_required":"Pick at least one IR emitter.","adddev.create":"Create","dup.heading":"Duplicate device","dup.hint_duplicating":"Duplicating {name}.","dup.hint_body":"The new device gets a copy of every command, action mapping, and emitter assignment. You can change anything afterward.","dup.duplicating":"Duplicating...","dup.duplicate":"Duplicate","promote.description":"Create a new HAIR device. You can then assign captured signals to it as commands.","capture.listening":"Listening for IR signal…","capture.instruction":'Point your remote at the IR receiver and press the "{name}" button.',"capture.remaining":"{seconds}s remaining","capture.captured":"Signal Captured!","capture.protocol":"Protocol: {protocol}","capture.protocol_raw":"Raw","capture.verify":"Did it work? Press Test to verify.","capture.test":"▶ Test","capture.recapture":"↻ Re-capture","capture.save_next":"Save & Learn Next ▶▶","capture.no_signal":"⚠ No signal detected","capture.tip_point":"Point the remote directly at the IR receiver","capture.tip_closer":"Move closer (within 3 feet / 1 meter)","capture.tip_hold":"Press and hold the button briefly","capture.try_again":"↻ Try Again","capture.duplicate":"⚠ Duplicate Signal Detected","capture.duplicate_instruction":'This matches your "{name}" command. Some remotes use the same signal for multiple buttons.',"capture.recapture_different":"Re-capture Different","capture.save_anyway":"Save Anyway","capture.error":"⚠ Capture Error","capture.learning":'Learning: "{name}"',"test_emitter.heading":"Send from","test_emitter.sending":"Sending...","test_emitter.send":"Send","createremote.heading":"Create Remote","createremote.type":"Type","createremote.blank":"Blank remote","createremote.from_library":"From code library","createremote.model":"Model","createremote.select_model":"Select a model","popover.assigned_to":"Assigned to","popover.new_assignment":"+ new assignment","popover.open_in_devices":"Open {name} in Devices","popover.triggers":"Triggers","popover.new_trigger":"+ new trigger","popover.any_receiver":"Any receiver","popover.n_more":"{name} + {count} more","cmdrow.rename":"Click to rename","cmdrow.tx_raw_on":"Replaying the captured Pronto. Click to transmit clean decoded packet timings instead.","cmdrow.tx_raw_off":"Transmitting clean decoded packet timings. Click to replay the captured Pronto instead.","cmdrow.sends_times":"Sends this command {count} times","cmdrow.dittos":"Appends {count} NEC dittos","cmdrow.raw_timings":"RAW: {count} timings","cmdrow.not_learned":"Not yet learned","cmdrow.edit_code":"View or edit code","cmdrow.map_action":"Assign action mapping","cmdrow.actions":"ACTIONS","cmdrow.test":"Test","cmdrow.trigger":"Trigger","cmdrow.edit_trigger":"Edit trigger","cmdrow.create_trigger":"Create trigger","cmdrow.delete":"Delete","cmdrow.learn":"Learn","trigger.alias_tag":"alias","trigger.event":"Trigger Event","trigger.edit_heading":"Edit Trigger","trigger.create_heading":"Create Trigger","trigger.mirror_hint":"Fires when this signal arrives from outside Home Assistant (a physical remote or another app), never on the house's own sends.","trigger.name_label":"Trigger Name","trigger.name_placeholder":"e.g. TV Power","trigger.min_hits":"Min Hits","trigger.min_hits_hint":"Number of presses within 5s to fire","trigger.scope_hint":"Fires once per press, regardless of how many scoped receivers observe the signal.","trigger.save_failed":"Save failed","common.saving":"Saving...","common.update":"Update","common.create":"Create","common.delete":"Delete","assign.heading":"Assign Signal","assign.hits":"{count} hits","assign.mode_existing":"Existing Device","assign.mode_new":"New Device","assign.send_times":"Send times","assign.send_times_hint":"Transmit this command this many times per press, for devices that need a repeat. Default 1.","assign.ditto_count":"Ditto count","assign.ditto_title":"Append repeat frames after the main frame; some strict receivers need at least one to register the command.","assign.ditto_hint":"Append repeat frames after the main frame; some strict receivers require at least one to register the command.","assign.assigning":"Assigning...","assign.create_assign":"Create & Assign","assign.assign":"Assign","assign.target_device":"Target device","assign.no_devices":'No devices yet. Switch to "New Device" to create one.',"assign.select_device":"Select device...","assign.command_name":"Command name","assign.command_placeholder":"Enter command name","assign.select_command":"Select command...","assign.custom":"Custom...","assign.command_required":"Command name is required.","assign.target_required":"Select a target device.","assign.failed_duplicate":"Assignment failed. The signal may have a duplicate code on the target device.","pluckdlg.blaster_required":"Pick a blaster to pluck from.","pluckdlg.appliance_required":"Appliance is required.","pluckdlg.add_heading":"Add Blaster","pluckdlg.loading_blasters":"Loading blasters...","pluckdlg.pluck_from":"Pluck from","pluckdlg.select_blaster":"Select a blaster","pluckdlg.appliance":"Appliance","pluckdlg.appliance_placeholder":"e.g. candles","pluckdlg.name_placeholder":"e.g. Living Room candles","pluckdlg.signal_heading":"Pluck Signal","pluckdlg.pluck_failed":"Pluck failed.","pluckdlg.no_response":"No response from blaster. Try again.","pluckdlg.recognized_as":"Recognized as {protocol}","pluckdlg.valid_pronto":"Valid Pronto code","pluckdlg.command_help":"The name you gave this code when you learned it in the vendor app.","pluckdlg.command_placeholder":"e.g. pwr_on","pluckdlg.plucking":"Plucking...","pluckdlg.pluck":"Pluck","pluckdlg.captured":"Captured","pluckdlg.remove_capture":"Remove this capture","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"No compatible blasters found. Install a supported IR integration (such as Tuya Local) and learn a code first.","editor.ditto_disabled_cmd":"Ditto count applies when the command transmits as NEC. Toggle the pill to NEC to enable.","editor.ditto_disabled":"Ditto count applies to decoded signals (NEC today). Raw Pronto codes transmit as captured.","editor.copied":"Copied","editor.press_copy":"Press Cmd/Ctrl+C","editor.valid":"Valid Pronto code","editor.not_valid":"Not valid yet","editor.burst_pair.one":"{count} burst pair","editor.burst_pair.other":"{count} burst pairs","editor.recognized_as":"Recognized as {protocol}","editor.snap_notice":"Carrier is {khz} kHz, off the IR standards. Some receivers reject it.","editor.snapping":"Snapping...","editor.snap_to":"Snap to {khz} kHz","editor.edit_command":"Edit command","editor.edit_signal":"Edit signal","editor.create_signal":"Create signal","common.save":"Save","editor.trigger_note_cmd":"This command has a trigger that will automatically re-point.","editor.trigger_note_sig":"This signal has a trigger that will automatically re-point.","editor.alias_label":"Alias","editor.alias_optional":"Alias (optional)","editor.pronto_code":"Pronto code","editor.select_all":"Select all (then Cmd/Ctrl+C)","editor.alias_placeholder":"e.g. Power","editor.send_times_title":"Transmit the whole command this many times as independent presses, for devices that need a repeat to register.","editor.ditto_title":"Append repeat frames after the main frame. Some strict receivers, notably commercial audio gear, need at least one to register the command.","editor.observed.one":"Observed at capture: {count} ditto","editor.observed.other":"Observed at capture: {count} dittos","rel.just_now":"just now","mirror.via":"via {name}","mirror.via_n":"via {count} emitters","mirror.not_heard":"not heard","mirror.heard_in":"last heard in {areas}","mirror.heard_by":"last heard by {names}","mirror.chip_automation":"Automation Send","mirror.chip_integration":"Integration Send","mirror.chip_test":"Manual Test Send","mirror.chip_device":"HAIR Device","mirror.chip_send":"Send","mirror.unknown_title":"Unknown IR signal sent","mirror.unknown_hint":"{name} fired, but nothing was close enough to hear what it said. Place a receiver in earshot to catch the next send.","mirror.the_blaster":"The blaster","mirror.sent":"Sent!","mirror.sent_all_n":"Sent! ({sent}/{total})","mirror.sent_partial":"Sent ({sent}/{total})","mirror.failed":"Failed","mirror.error":"Error","mirror.sending":"Sending...","mirror.test":"Test","mirror.stat_sends":"SENDS","mirror.stat_not_heard":"NOT HEARD","mirror.stat_emitters":"EMITTERS","mirror.stat_signals":"SIGNALS","mirror.last_send_ago":"last send {rel} ago","mirror.last_send_just":"last send just now","mirror.no_receivers":"no receivers","mirror.filter_all":"All ({count})","mirror.filter_not_heard":"Not heard ({count})","mirror.search":"Search sends...","mirror.no_match":"No sends match.","mirror.signals.one":"{count} signal","mirror.signals.other":"{count} signals","mirror.sends_times":"Sends this signal {count} times","mirror.assign_disabled":"Identity unknown -- nothing was heard back to assign","mirror.assigned_one":"Assigned to {device} / {command}","mirror.assigned_n":"Assigned to {count} commands:","mirror.assign_title":"Assign this signal to a HAIR device","mirror.test_title":"Send this signal through an emitter to test it","mirror.test_disabled":"Identity unknown -- nothing to send","mirror.trigger_disabled":"Identity unknown -- nothing to bind","mirror.trigger_edit":"Edit trigger(s) for this signal","mirror.trigger_create":"Fires when this signal arrives from outside Home Assistant","mirror.delete_title":"Clear this entry (it returns on the next send)","mirror.empty_title":"Nothing sent yet","mirror.empty_sub":"Commands sent by HAIR devices, automations, or any integration on the infrared platform will appear here, with where they went and who heard them.","mirror.del_trigger_title":"Delete Trigger","mirror.del_trigger_msg":"Remove this trigger permanently? Automations using it will stop firing.","mirror.clear_title":"Clear Mirror Entry","mirror.clear_msg":"Remove this entry from the Mirror? It will come back the next time this signal is sent.","common.delete_failed":"Delete failed: {message}","device_type.other_card":"IR Device","devlist.loading":"Loading IR devices...","devlist.empty_title":"No IR devices yet","devlist.empty_sub":"Add your first device to get started.","devlist.add_device_plus":"+ Add Device","devlist.title":"HAIR Devices","devlist.add_device":"Add Device","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"No TX","devlist.rx_native_title":"Receives via HA's native infrared platform","devlist.rx_bridge_active":"Legacy bridge still active. Native receiver supersedes it -- you can remove the on_pronto: block from your ESPHome config.","devlist.rx_bridge_title":"Receives via legacy ESPHome event-bus bridge","devlist.rx_upgrade_title":"Upgrade to HA 2026.6+ for native receiver support","devlist.tx_native_title":"Sends via HA's native infrared platform","devlist.blasters":"Blasters (Pluckable)","devlist.emitters":"Emitters","devlist.receivers":"Receivers","devlist.proxies":"Proxies","devlist.hits_badge":"{count}x hits","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Delete trigger","devlist.delete_device":"Delete device","devlist.open_plucker_title":"Open in the Plucker","devlist.open_plucker":"Open in Plucker","devlist.del_trigger_msg":'Remove "{name}"? The associated HA event entity will also be removed.',"devlist.del_device_title":"Delete Device","devlist.del_device_msg":'Remove "{name}"? Commands, action mappings, and emitter assignments will be deleted. Triggers are unaffected.',"common.close":"Close","devdetail.name_updated":"Name updated","devdetail.type_updated":"Device type updated","devdetail.emitters_updated":"Emitters updated","devdetail.update_failed":"Update failed: {message}","devdetail.reorder_failed":"Reorder failed: {message}","devdetail.mapped_to":"Mapped to {action}","devdetail.mapping_cleared":"Mapping cleared","devdetail.mapping_failed":"Mapping failed: {message}","devdetail.sent_cmd":'Sent "{name}"',"devdetail.send_failed":"Send failed: {message}","devdetail.cmd_updated":"Command updated","devdetail.cmd_updated_repointed":"Command updated. Re-pointed trigger {names}.","devdetail.rename_failed":"Rename failed: {message}","devdetail.removed":'Removed "{name}"',"devdetail.saved":'Saved "{name}"',"devdetail.type":"Type","devdetail.commands":"Commands ({count})","devdetail.no_commands":"No commands yet. Add one below.","devdetail.drag":"Drag to reorder","devdetail.map_action":"Map action","devdetail.none_clear":"None (clear)","devdetail.sniff_title":"Capture a new signal in the Sniffer","devdetail.sniffed":"+ Sniffed Signal","devdetail.clip_title":"Paste a new signal in Clips","devdetail.clipped":"+ Clipped Signal","devdetail.mirror_title":"Overhear a send in the Mirror","devdetail.mirrored":"+ Mirrored Signal","devdetail.del_device_title":"Delete {name}?","devdetail.del_device_msg":"This removes all captured commands and the auto-created entity. The action cannot be undone.","devdetail.del_cmd_title":"Delete command?","devdetail.del_cmd_msg":'Remove "{name}"? This cannot be undone.',"devdetail.del_trigger_msg":"Remove this trigger? The associated HA event entity will also be removed.","rel.min_ago":"{count} min ago","rel.h_ago":"{count}h ago","rel.d_ago":"{count}d ago","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} remote","sniffer.remotes.other":"{count} remotes","sniffer.scanning":"Scanning for signals...","sniffer.empty_title":"No unknown signals detected","sniffer.empty_body":"When unrecognized IR signals are received by your ESPHome devices, they will appear here automatically.","sniffer.empty_hint":"Try pressing a button on a remote that hasn't been configured yet.","sniffer.norx_title":"No IR receiver is set up","sniffer.norx_body":"HAIR has no way to receive IR signals yet, so the Sniffer cannot capture anything.","sniffer.norx_hint":"Set up an ESPHome receiver with the infrared platform, or check Settings, then Devices and Services, to confirm your IR device is adopted.","sniffer.show_dismissed_title":"Restore previously hidden remotes","sniffer.show_dismissed":"Show Dismissed","sniffer.hide_dismissed":"Hide Dismissed","sniffer.clear_all_title":"Wipe the entire unknown catalog AND the dismiss list. Use Show Dismissed before Clear All if you want to retain individual dismissed entries.","sniffer.clear_all":"Clear All","sniffer.del_signal_title":"Delete Signal","sniffer.del_signal_msg":"Remove this signal permanently? This cannot be undone.","sniffer.clear_all_confirm_title":"Clear All Signals","sniffer.clear_all_confirm_msg":"Remove all unknown signals and devices? This cannot be undone.","sniffer.hair_device":"HAIR Device","sniffer.promote":"Promote","sniffer.dismissed":"dismissed","sniffer.restore":"Restore","sniffer.dismiss":"Dismiss","sniffer.addr":"addr: {address}","sniffer.signals_head":"Signals ({count})","sniffer.first_seen":"First seen: {time}","sniffer.restore_first":"Restore this remote first","sniffer.trigger_create":"Create an HA event entity that fires on this signal","common.raw":"RAW","sniffer.hit_word.one":"hit","sniffer.hit_word.other":"hits","sniffer.signal_word.one":"signal","sniffer.signal_word.other":"signals","common.loading_plain":"Loading...","clips.title":"HAIR Clipper","clips.add_remote":"+ Add Remote","clips.empty_title":"No virtual remotes yet","clips.empty_body":"Clipper lets you build remotes by pasting Pronto codes. Create a remote, then add a signal for each button.","clips.empty_hint":'Click "+ Add Remote" above to start a clipped remote.',"clips.clear_all_title":"Delete all clipped remotes and their signals. Sniffed signals are untouched.","clips.remote_fallback":"Remote","clips.add_signal_title":"Add a signal to this remote","clips.add_signal":"+ Add Signal","clips.no_signals":'No signals yet. Click "+ Add Signal" to paste a Pronto code.',"clips.delete_remote_title":"Delete this remote and all its signals","clips.delete_remote":"Delete remote","clips.test_title":"Send this signal through an emitter","clips.clear_all_confirm_title":"Clear All Clips","clips.clear_all_confirm_msg":"Remove all clipped remotes and their signals? This cannot be undone. Sniffed signals are not affected.","clips.del_remote_confirm_title":"Delete Remote","clips.del_remote_msg_n.one":'Remove "{name}" and its {count} signal? This cannot be undone.',"clips.del_remote_msg_n.other":'Remove "{name}" and its {count} signals? This cannot be undone.',"clips.del_remote_msg":'Remove "{name}"? This cannot be undone.',"pluck.vendor_unavailable":"This blaster's integration is not available right now. Make sure the vendor integration is loaded.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Add Blaster","pluck.empty_title":"No plucked blasters yet","pluck.empty_body":"The Plucker imports IR codes from your existing blasters so you can use them in HAIR without re-learning each one.","pluck.empty_hint":'Click "+ Add Blaster" above to mirror a blaster.',"pluck.clear_all_title":"Delete all plucked blasters and their signals. Sniffed and clipped signals are untouched.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Create a HAIR device from this blaster","pluck.pluck_signal_title":"Pluck a code off this blaster","pluck.pluck_signal":"+ Pluck Signal","pluck.no_signals":'No signals yet. Click "+ Pluck Signal" to pull a code off this blaster.',"pluck.delete_blaster_title":"Delete this blaster and all its signals","pluck.delete_blaster":"Delete blaster","pluck.clear_all_confirm_title":"Clear All Plucked","pluck.clear_all_confirm_msg":"Remove all plucked blasters and their signals? This cannot be undone. Sniffed and clipped signals are not affected.","pluck.del_blaster_confirm_title":"Delete Blaster","devdetail.custom_action":"Custom...","devdetail.custom_action_placeholder":"e.g. temp_30","devdetail.set":"Set","vocab.back_return":"Back/Return","vocab.brightness_down":"Brightness Down","vocab.brightness_up":"Brightness Up","vocab.channel_down":"Channel Down","vocab.channel_up":"Channel Up","vocab.close":"Close","vocab.color_temp_cooler":"Color Temp Cooler","vocab.color_temp_warmer":"Color Temp Warmer","vocab.down":"Down","vocab.fan_auto":"Fan: Auto","vocab.fan_high":"Fan: High","vocab.fan_low":"Fan: Low","vocab.fan_medium":"Fan: Medium","vocab.fast_forward":"Fast Forward","vocab.guide":"Guide","vocab.left":"Left","vocab.menu":"Menu","vocab.mode_auto":"Mode: Auto","vocab.mode_cool":"Mode: Cool","vocab.mode_dry":"Mode: Dry","vocab.mode_fan":"Mode: Fan","vocab.mode_heat":"Mode: Heat","vocab.mute":"Mute","vocab.off":"Off","vocab.on":"On","vocab.open":"Open","vocab.oscillate":"Oscillate","vocab.pause":"Pause","vocab.play":"Play","vocab.power":"Power","vocab.power_off":"Power Off","vocab.power_on":"Power On","vocab.power_toggle":"Power Toggle","vocab.rewind":"Rewind","vocab.right":"Right","vocab.select_ok":"Select/OK","vocab.source_input":"Source/Input","vocab.speed_down":"Speed Down","vocab.speed_up":"Speed Up","vocab.stop":"Stop","vocab.swing_toggle":"Swing Toggle","vocab.timer":"Timer","vocab.up":"Up","vocab.volume_down":"Volume Down","vocab.volume_up":"Volume Up"};const ve={de:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Wird geladen…","panel.load_failed":"Geräte konnten nicht geladen werden: {message}","panel.open_menu":"Menü öffnen","panel.tab.devices":"Geräte","panel.tagline.devices":"Verwalte deine IR-Geräte und die Hardware dahinter.","panel.tagline.sniffer":"Fange IR-Codes live aus der Luft ein.","panel.tagline.clips":"Baue Fernbedienungen durch Einfügen bekannter IR-Codes.","panel.tagline.plucker":"Ziehe IR-Codes aus vorhandenen Blastern.","panel.tagline.mirror":"Sieh die Infrarot-Übertragungen von Home Assistant live.","common.confirm":"Bestätigen","common.cancel":"Abbrechen","common.are_you_sure":"Bist du sicher?","common.remove":"Entfernen","alias.placeholder":"Alias für dieses Signal","alias.tag":"Alias","alias.clear":"Alias löschen","alias.edit":"Zum Bearbeiten des Alias klicken","alias.name":"Klicken, um dieses Signal zu benennen","picker.emitters_label":"IR-Sender","picker.add_emitter":"+ Sender hinzufügen...","picker.no_emitters":"Keine IR-Sender gefunden.","picker.all_emitters_selected":"Alle Sender ausgewählt.","picker.receivers_label":"Über Empfänger:","picker.add_receiver":"+ Empfänger hinzufügen...","picker.no_receivers":"Keine IR-Empfänger gefunden.","picker.all_receivers_selected":"Alle Empfänger ausgewählt.","device_type.media_player":"Medienplayer","device_type.ac":"Klimaanlage","device_type.fan":"Ventilator","device_type.light":"Licht","device_type.switch":"Schalter","device_type.screen":"Leinwand / Rollo","device_type.other":"Sonstiges","common.name":"Name","common.device_type":"Gerätetyp","common.name_required":"Name ist erforderlich.","common.creating":"Wird erstellt...","common.device_name_placeholder":"z. B. Wohnzimmer-TV","promote.heading":"Zum Gerät befördern","promote.device_name":"Gerätename","promote.device_name_required":"Gerätename ist erforderlich.","promote.emitter_required":"Wähle mindestens einen IR-Sender.","promote.create_device":"Gerät erstellen","adddev.heading":"Gerät hinzufügen","adddev.emitter_required":"Wähle mindestens einen IR-Sender.","adddev.create":"Erstellen","dup.heading":"Gerät duplizieren","dup.hint_duplicating":"{name} wird dupliziert.","dup.hint_body":"Das neue Gerät erhält eine Kopie aller Befehle, Aktionszuordnungen und Senderzuweisungen. Du kannst danach alles ändern.","dup.duplicating":"Wird dupliziert...","dup.duplicate":"Duplizieren","promote.description":"Erstelle ein neues HAIR-Gerät. Danach kannst du ihm eingefangene Signale als Befehle zuweisen.","capture.listening":"Warte auf IR-Signal…","capture.instruction":'Richte deine Fernbedienung auf den IR-Empfänger und drücke die Taste "{name}".',"capture.remaining":"{seconds}s verbleibend","capture.captured":"Signal eingefangen!","capture.protocol":"Protokoll: {protocol}","capture.protocol_raw":"Roh","capture.verify":"Hat es funktioniert? Drücke Testen zum Überprüfen.","capture.test":"▶ Testen","capture.recapture":"↻ Neu einfangen","capture.save_next":"Speichern und nächste lernen ▶▶","capture.no_signal":"⚠ Kein Signal erkannt","capture.tip_point":"Richte die Fernbedienung direkt auf den IR-Empfänger","capture.tip_closer":"Geh näher heran (unter 1 Meter)","capture.tip_hold":"Halte die Taste kurz gedrückt","capture.try_again":"↻ Erneut versuchen","capture.duplicate":"⚠ Doppeltes Signal erkannt","capture.duplicate_instruction":'Dieses Signal entspricht deinem Befehl "{name}". Manche Fernbedienungen nutzen dasselbe Signal für mehrere Tasten.',"capture.recapture_different":"Anderes einfangen","capture.save_anyway":"Trotzdem speichern","capture.error":"⚠ Einfangfehler","capture.learning":'Lerne: "{name}"',"test_emitter.heading":"Senden von","test_emitter.sending":"Wird gesendet...","test_emitter.send":"Senden","createremote.heading":"Fernbedienung erstellen","createremote.type":"Typ","createremote.blank":"Leere Fernbedienung","createremote.from_library":"Aus der Code-Bibliothek","createremote.model":"Modell","createremote.select_model":"Modell auswählen","popover.assigned_to":"Zugewiesen an","popover.new_assignment":"+ neue Zuweisung","popover.open_in_devices":"{name} in Geräten öffnen","popover.triggers":"Auslöser","popover.new_trigger":"+ neuer Auslöser","popover.any_receiver":"Beliebiger Empfänger","popover.n_more":"{name} + {count} weitere","cmdrow.rename":"Zum Umbenennen klicken","cmdrow.tx_raw_on":"Spielt das eingefangene Pronto ab. Klicken, um stattdessen saubere dekodierte Pakettimings zu senden.","cmdrow.tx_raw_off":"Sendet saubere dekodierte Pakettimings. Klicken, um stattdessen das eingefangene Pronto abzuspielen.","cmdrow.sends_times":"Sendet diesen Befehl {count}-mal","cmdrow.dittos":"Hängt {count} NEC-Dittos an","cmdrow.raw_timings":"RAW: {count} Timings","cmdrow.not_learned":"Noch nicht gelernt","cmdrow.edit_code":"Code ansehen oder bearbeiten","cmdrow.map_action":"Aktionszuordnung zuweisen","cmdrow.actions":"AKTIONEN","cmdrow.test":"Testen","cmdrow.trigger":"Auslöser","cmdrow.edit_trigger":"Auslöser bearbeiten","cmdrow.create_trigger":"Auslöser erstellen","cmdrow.delete":"Löschen","cmdrow.learn":"Lernen","trigger.alias_tag":"Alias","trigger.event":"Auslöse-Ereignis","trigger.edit_heading":"Auslöser bearbeiten","trigger.create_heading":"Auslöser erstellen","trigger.mirror_hint":"Löst aus, wenn dieses Signal von außerhalb von Home Assistant kommt (eine physische Fernbedienung oder eine andere App), nie bei den eigenen Sendungen des Hauses.","trigger.name_label":"Auslösername","trigger.name_placeholder":"z. B. TV Ein/Aus","trigger.min_hits":"Min. Treffer","trigger.min_hits_hint":"Anzahl Tastendrücke innerhalb von 5s zum Auslösen","trigger.scope_hint":"Löst einmal pro Tastendruck aus, egal wie viele erfasste Empfänger das Signal beobachten.","trigger.save_failed":"Speichern fehlgeschlagen","common.saving":"Wird gespeichert...","common.update":"Aktualisieren","common.create":"Erstellen","common.delete":"Löschen","assign.heading":"Signal zuweisen","assign.hits":"{count} Empfänge","assign.mode_existing":"Vorhandenes Gerät","assign.mode_new":"Neues Gerät","assign.send_times":"Sendeanzahl","assign.send_times_hint":"Sendet diesen Befehl pro Tastendruck so oft, für Geräte, die eine Wiederholung brauchen. Standard 1.","assign.ditto_count":"Ditto-Anzahl","assign.ditto_title":"Hängt Wiederholungsrahmen an den Hauptrahmen an; manche strengen Empfänger verlangen mindestens einen, um den Befehl zu registrieren.","assign.ditto_hint":"Hängt Wiederholungsrahmen an den Hauptrahmen an; manche strengen Empfänger verlangen mindestens einen, um den Befehl zu registrieren.","assign.assigning":"Wird zugewiesen...","assign.create_assign":"Erstellen und zuweisen","assign.assign":"Zuweisen","assign.target_device":"Zielgerät","assign.no_devices":'Noch keine Geräte. Wechsle zu "Neues Gerät", um eines zu erstellen.',"assign.select_device":"Gerät auswählen...","assign.command_name":"Befehlsname","assign.command_placeholder":"Befehlsname eingeben","assign.select_command":"Befehl auswählen...","assign.custom":"Benutzerdefiniert...","assign.command_required":"Befehlsname ist erforderlich.","assign.target_required":"Wähle ein Zielgerät.","assign.failed_duplicate":"Zuweisung fehlgeschlagen. Das Signal hat möglicherweise einen doppelten Code auf dem Zielgerät.","pluckdlg.blaster_required":"Wähle einen Blaster zum Ziehen.","pluckdlg.appliance_required":"Gerät ist erforderlich.","pluckdlg.add_heading":"Blaster hinzufügen","pluckdlg.loading_blasters":"Blaster werden geladen...","pluckdlg.pluck_from":"Ziehen von","pluckdlg.select_blaster":"Blaster auswählen","pluckdlg.appliance":"Gerät","pluckdlg.appliance_placeholder":"z. B. Kerzen","pluckdlg.name_placeholder":"z. B. Wohnzimmer-Kerzen","pluckdlg.signal_heading":"Signal ziehen","pluckdlg.pluck_failed":"Ziehen fehlgeschlagen.","pluckdlg.no_response":"Keine Antwort vom Blaster. Versuch es erneut.","pluckdlg.recognized_as":"Erkannt als {protocol}","pluckdlg.valid_pronto":"Gültiger Pronto-Code","pluckdlg.command_help":"Der Name, den du diesem Code beim Lernen in der Hersteller-App gegeben hast.","pluckdlg.command_placeholder":"z. B. pwr_on","pluckdlg.plucking":"Wird gezogen...","pluckdlg.pluck":"Ziehen","pluckdlg.captured":"Eingefangen","pluckdlg.remove_capture":"Diese Aufnahme entfernen","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Keine kompatiblen Blaster gefunden. Installiere eine unterstützte IR-Integration (z. B. Tuya Local) und lerne zuerst einen Code.","editor.ditto_disabled_cmd":"Die Ditto-Anzahl gilt, wenn der Befehl als NEC gesendet wird. Stelle die Pille auf NEC, um sie zu aktivieren.","editor.ditto_disabled":"Die Ditto-Anzahl gilt für dekodierte Signale (heute NEC). Rohe Pronto-Codes werden wie eingefangen gesendet.","editor.copied":"Kopiert","editor.press_copy":"Drücke Cmd/Strg+C","editor.valid":"Gültiger Pronto-Code","editor.not_valid":"Noch nicht gültig","editor.burst_pair.one":"{count} Impulspaar","editor.burst_pair.other":"{count} Impulspaare","editor.recognized_as":"Erkannt als {protocol}","editor.snap_notice":"Der Träger liegt bei {khz} kHz, außerhalb der IR-Standards. Manche Empfänger lehnen ihn ab.","editor.snapping":"Wird angepasst...","editor.snap_to":"Auf {khz} kHz anpassen","editor.edit_command":"Befehl bearbeiten","editor.edit_signal":"Signal bearbeiten","editor.create_signal":"Signal erstellen","common.save":"Speichern","editor.trigger_note_cmd":"Dieser Befehl hat einen Auslöser, der sich automatisch neu ausrichtet.","editor.trigger_note_sig":"Dieses Signal hat einen Auslöser, der sich automatisch neu ausrichtet.","editor.alias_label":"Alias","editor.alias_optional":"Alias (optional)","editor.pronto_code":"Pronto-Code","editor.select_all":"Alles auswählen (dann Cmd/Strg+C)","editor.alias_placeholder":"z. B. Power","editor.send_times_title":"Sendet den ganzen Befehl so oft als unabhängige Tastendrücke, für Geräte, die eine Wiederholung brauchen.","editor.ditto_title":"Hängt Wiederholungsrahmen an den Hauptrahmen an. Manche strengen Empfänger, vor allem professionelles Audio-Equipment, verlangen mindestens einen.","editor.observed.one":"Bei der Aufnahme beobachtet: {count} Ditto","editor.observed.other":"Bei der Aufnahme beobachtet: {count} Dittos","rel.just_now":"gerade eben","mirror.via":"über {name}","mirror.via_n":"über {count} Sender","mirror.not_heard":"nicht gehört","mirror.heard_in":"zuletzt gehört in {areas}","mirror.heard_by":"zuletzt gehört von {names}","mirror.chip_automation":"Automations-Sendung","mirror.chip_integration":"Integrations-Sendung","mirror.chip_test":"Manuelle Testsendung","mirror.chip_device":"HAIR-Gerät","mirror.chip_send":"Sendung","mirror.unknown_title":"Unbekanntes IR-Signal gesendet","mirror.unknown_hint":"{name} hat gefeuert, aber nichts war nah genug, um zu hören, was gesagt wurde. Stelle einen Empfänger in Hörweite, um die nächste Sendung einzufangen.","mirror.the_blaster":"Der Blaster","mirror.sent":"Gesendet!","mirror.sent_all_n":"Gesendet! ({sent}/{total})","mirror.sent_partial":"Gesendet ({sent}/{total})","mirror.failed":"Fehlgeschlagen","mirror.error":"Fehler","mirror.sending":"Wird gesendet...","mirror.test":"Testen","mirror.stat_sends":"SENDUNGEN","mirror.stat_not_heard":"NICHT GEHÖRT","mirror.stat_emitters":"SENDER","mirror.stat_signals":"SIGNALE","mirror.last_send_ago":"letzte Sendung vor {rel}","mirror.last_send_just":"letzte Sendung gerade eben","mirror.no_receivers":"keine Empfänger","mirror.filter_all":"Alle ({count})","mirror.filter_not_heard":"Nicht gehört ({count})","mirror.search":"Sendungen durchsuchen...","mirror.no_match":"Keine Sendung passt.","mirror.signals.one":"{count} Signal","mirror.signals.other":"{count} Signale","mirror.sends_times":"Sendet dieses Signal {count}-mal","mirror.assign_disabled":"Identität unbekannt -- nichts zurückgehört zum Zuweisen","mirror.assigned_one":"Zugewiesen an {device} / {command}","mirror.assigned_n":"Zugewiesen an {count} Befehle:","mirror.assign_title":"Dieses Signal einem HAIR-Gerät zuweisen","mirror.test_title":"Dieses Signal über einen Sender zum Testen senden","mirror.test_disabled":"Identität unbekannt -- nichts zu senden","mirror.trigger_disabled":"Identität unbekannt -- nichts zu verknüpfen","mirror.trigger_edit":"Auslöser dieses Signals bearbeiten","mirror.trigger_create":"Löst aus, wenn dieses Signal von außerhalb von Home Assistant kommt","mirror.delete_title":"Diesen Eintrag löschen (kommt bei der nächsten Sendung zurück)","mirror.empty_title":"Noch nichts gesendet","mirror.empty_sub":"Befehle von HAIR-Geräten, Automationen oder jeder Integration auf der Infrarot-Plattform erscheinen hier, mit Ziel und wer sie gehört hat.","mirror.del_trigger_title":"Auslöser löschen","mirror.del_trigger_msg":"Diesen Auslöser dauerhaft entfernen? Automationen, die ihn nutzen, lösen nicht mehr aus.","mirror.clear_title":"Mirror-Eintrag löschen","mirror.clear_msg":"Diesen Eintrag aus dem Mirror entfernen? Er kommt zurück, wenn dieses Signal das nächste Mal gesendet wird.","common.delete_failed":"Löschen fehlgeschlagen: {message}","device_type.other_card":"IR-Gerät","devlist.loading":"IR-Geräte werden geladen...","devlist.empty_title":"Noch keine IR-Geräte","devlist.empty_sub":"Füge dein erstes Gerät hinzu, um loszulegen.","devlist.add_device_plus":"+ Gerät hinzufügen","devlist.title":"HAIR-Geräte","devlist.add_device":"Gerät hinzufügen","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Kein TX","devlist.rx_native_title":"Empfängt über HAs native Infrarot-Plattform","devlist.rx_bridge_active":"Die alte Brücke ist noch aktiv. Der native Empfänger ersetzt sie -- du kannst den on_pronto:-Block aus deiner ESPHome-Konfiguration entfernen.","devlist.rx_bridge_title":"Empfängt über die alte ESPHome-Ereignisbus-Brücke","devlist.rx_upgrade_title":"Aktualisiere auf HA 2026.6+ für native Empfängerunterstützung","devlist.tx_native_title":"Sendet über HAs native Infrarot-Plattform","devlist.blasters":"Blaster (ziehbar)","devlist.emitters":"Sender","devlist.receivers":"Empfänger","devlist.proxies":"Proxys","devlist.hits_badge":"{count}x Empfänge","devlist.on":"AN","devlist.off":"AUS","devlist.delete_trigger":"Auslöser löschen","devlist.delete_device":"Gerät löschen","devlist.open_plucker_title":"Im Plucker öffnen","devlist.open_plucker":"Im Plucker öffnen","devlist.del_trigger_msg":'"{name}" entfernen? Die zugehörige HA-Ereignis-Entität wird ebenfalls entfernt.',"devlist.del_device_title":"Gerät löschen","devlist.del_device_msg":'"{name}" entfernen? Befehle, Aktionszuordnungen und Senderzuweisungen werden gelöscht. Auslöser bleiben unberührt.',"common.close":"Schließen","devdetail.name_updated":"Name aktualisiert","devdetail.type_updated":"Gerätetyp aktualisiert","devdetail.emitters_updated":"Sender aktualisiert","devdetail.update_failed":"Aktualisierung fehlgeschlagen: {message}","devdetail.reorder_failed":"Neuordnung fehlgeschlagen: {message}","devdetail.mapped_to":"Zugeordnet zu {action}","devdetail.mapping_cleared":"Zuordnung gelöscht","devdetail.mapping_failed":"Zuordnung fehlgeschlagen: {message}","devdetail.sent_cmd":'"{name}" gesendet',"devdetail.send_failed":"Senden fehlgeschlagen: {message}","devdetail.cmd_updated":"Befehl aktualisiert","devdetail.cmd_updated_repointed":"Befehl aktualisiert. Auslöser {names} neu ausgerichtet.","devdetail.rename_failed":"Umbenennen fehlgeschlagen: {message}","devdetail.removed":'"{name}" entfernt',"devdetail.saved":'"{name}" gespeichert',"devdetail.type":"Typ","devdetail.commands":"Befehle ({count})","devdetail.no_commands":"Noch keine Befehle. Füge unten einen hinzu.","devdetail.drag":"Ziehen zum Neuordnen","devdetail.map_action":"Aktion zuordnen","devdetail.none_clear":"Keine (löschen)","devdetail.sniff_title":"Ein neues Signal im Sniffer einfangen","devdetail.sniffed":"+ Geschnüffeltes Signal","devdetail.clip_title":"Ein neues Signal in Clips einfügen","devdetail.clipped":"+ Eingefügtes Signal","devdetail.mirror_title":"Eine Sendung im Mirror belauschen","devdetail.mirrored":"+ Signal aus dem Mirror","devdetail.del_device_title":"{name} löschen?","devdetail.del_device_msg":"Das entfernt alle eingefangenen Befehle und die automatisch erstellte Entität. Das kann nicht rückgängig gemacht werden.","devdetail.del_cmd_title":"Befehl löschen?","devdetail.del_cmd_msg":'"{name}" entfernen? Das kann nicht rückgängig gemacht werden.',"devdetail.del_trigger_msg":"Diesen Auslöser entfernen? Die zugehörige HA-Ereignis-Entität wird ebenfalls entfernt.","rel.min_ago":"vor {count} Min.","rel.h_ago":"vor {count}h","rel.d_ago":"vor {count}d","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} Fernbedienung","sniffer.remotes.other":"{count} Fernbedienungen","sniffer.scanning":"Suche nach Signalen...","sniffer.empty_title":"Keine unbekannten Signale erkannt","sniffer.empty_body":"Wenn deine ESPHome-Geräte unerkannte IR-Signale empfangen, erscheinen sie hier automatisch.","sniffer.empty_hint":"Drücke eine Taste auf einer noch nicht eingerichteten Fernbedienung.","sniffer.norx_title":"Kein IR-Empfänger eingerichtet","sniffer.norx_body":"HAIR kann noch keine IR-Signale empfangen, daher kann der Sniffer nichts einfangen.","sniffer.norx_hint":"Richte einen ESPHome-Empfänger mit der Infrarot-Plattform ein oder prüfe unter Einstellungen, dann Geräte und Dienste, ob dein IR-Gerät eingebunden ist.","sniffer.show_dismissed_title":"Zuvor ausgeblendete Fernbedienungen wiederherstellen","sniffer.show_dismissed":"Verworfene anzeigen","sniffer.hide_dismissed":"Verworfene ausblenden","sniffer.clear_all_title":"Leert den gesamten Katalog unbekannter Signale UND die Verworfen-Liste. Nutze Verworfene anzeigen vor Alles löschen, wenn du einzelne verworfene Einträge behalten willst.","sniffer.clear_all":"Alles löschen","sniffer.del_signal_title":"Signal löschen","sniffer.del_signal_msg":"Dieses Signal dauerhaft entfernen? Das kann nicht rückgängig gemacht werden.","sniffer.clear_all_confirm_title":"Alle Signale löschen","sniffer.clear_all_confirm_msg":"Alle unbekannten Signale und Geräte entfernen? Das kann nicht rückgängig gemacht werden.","sniffer.hair_device":"HAIR-Gerät","sniffer.promote":"Befördern","sniffer.dismissed":"verworfen","sniffer.restore":"Wiederherstellen","sniffer.dismiss":"Verwerfen","sniffer.addr":"Adr.: {address}","sniffer.signals_head":"Signale ({count})","sniffer.first_seen":"Zuerst gesehen: {time}","sniffer.restore_first":"Stelle zuerst diese Fernbedienung wieder her","sniffer.trigger_create":"Eine HA-Ereignis-Entität erstellen, die bei diesem Signal auslöst","common.raw":"RAW","sniffer.hit_word.one":"Treffer","sniffer.hit_word.other":"Treffer","sniffer.signal_word.one":"Signal","sniffer.signal_word.other":"Signale","common.loading_plain":"Wird geladen...","clips.title":"HAIR Clipper","clips.add_remote":"+ Fernbedienung hinzufügen","clips.empty_title":"Noch keine virtuellen Fernbedienungen","clips.empty_body":"Mit Clipper baust du Fernbedienungen durch Einfügen von Pronto-Codes. Erstelle eine Fernbedienung und füge dann für jede Taste ein Signal hinzu.","clips.empty_hint":'Klicke oben auf "+ Fernbedienung hinzufügen", um eine eingefügte Fernbedienung zu beginnen.',"clips.clear_all_title":"Löscht alle eingefügten Fernbedienungen und ihre Signale. Geschnüffelte Signale bleiben unberührt.","clips.remote_fallback":"Fernbedienung","clips.add_signal_title":"Ein Signal zu dieser Fernbedienung hinzufügen","clips.add_signal":"+ Signal hinzufügen","clips.no_signals":'Noch keine Signale. Klicke auf "+ Signal hinzufügen", um einen Pronto-Code einzufügen.',"clips.delete_remote_title":"Diese Fernbedienung und alle ihre Signale löschen","clips.delete_remote":"Fernbedienung löschen","clips.test_title":"Dieses Signal über einen Sender senden","clips.clear_all_confirm_title":"Alle Clips löschen","clips.clear_all_confirm_msg":"Alle eingefügten Fernbedienungen und ihre Signale entfernen? Das kann nicht rückgängig gemacht werden. Geschnüffelte Signale sind nicht betroffen.","clips.del_remote_confirm_title":"Fernbedienung löschen","clips.del_remote_msg_n.one":'"{name}" und sein {count} Signal entfernen? Das kann nicht rückgängig gemacht werden.',"clips.del_remote_msg_n.other":'"{name}" und seine {count} Signale entfernen? Das kann nicht rückgängig gemacht werden.',"clips.del_remote_msg":'"{name}" entfernen? Das kann nicht rückgängig gemacht werden.',"pluck.vendor_unavailable":"Die Integration dieses Blasters ist gerade nicht verfügbar. Stelle sicher, dass die Hersteller-Integration geladen ist.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Blaster hinzufügen","pluck.empty_title":"Noch keine gezogenen Blaster","pluck.empty_body":"Der Plucker importiert IR-Codes aus deinen vorhandenen Blastern, damit du sie in HAIR nutzen kannst, ohne jeden neu zu lernen.","pluck.empty_hint":'Klicke oben auf "+ Blaster hinzufügen", um einen Blaster zu spiegeln.',"pluck.clear_all_title":"Löscht alle gezogenen Blaster und ihre Signale. Geschnüffelte und eingefügte Signale bleiben unberührt.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Ein HAIR-Gerät aus diesem Blaster erstellen","pluck.pluck_signal_title":"Einen Code von diesem Blaster ziehen","pluck.pluck_signal":"+ Signal ziehen","pluck.no_signals":'Noch keine Signale. Klicke auf "+ Signal ziehen", um einen Code von diesem Blaster zu holen.',"pluck.delete_blaster_title":"Diesen Blaster und alle seine Signale löschen","pluck.delete_blaster":"Blaster löschen","pluck.clear_all_confirm_title":"Alle gezogenen löschen","pluck.clear_all_confirm_msg":"Alle gezogenen Blaster und ihre Signale entfernen? Das kann nicht rückgängig gemacht werden. Geschnüffelte und eingefügte Signale sind nicht betroffen.","pluck.del_blaster_confirm_title":"Blaster löschen","devdetail.custom_action":"Benutzerdefiniert...","devdetail.custom_action_placeholder":"z. B. temp_30","devdetail.set":"Setzen","vocab.back_return":"Zurück","vocab.brightness_down":"Helligkeit -","vocab.brightness_up":"Helligkeit +","vocab.channel_down":"Kanal -","vocab.channel_up":"Kanal +","vocab.close":"Schließen","vocab.color_temp_cooler":"Kälteres Weiß","vocab.color_temp_warmer":"Wärmeres Weiß","vocab.down":"Runter","vocab.fan_auto":"Lüfter: Auto","vocab.fan_high":"Lüfter: Hoch","vocab.fan_low":"Lüfter: Niedrig","vocab.fan_medium":"Lüfter: Mittel","vocab.fast_forward":"Vorspulen","vocab.guide":"Guide","vocab.left":"Links","vocab.menu":"Menü","vocab.mode_auto":"Modus: Auto","vocab.mode_cool":"Modus: Kühlen","vocab.mode_dry":"Modus: Entfeuchten","vocab.mode_fan":"Modus: Lüften","vocab.mode_heat":"Modus: Heizen","vocab.mute":"Stumm","vocab.off":"Aus","vocab.on":"Ein","vocab.open":"Öffnen","vocab.oscillate":"Schwenken","vocab.pause":"Pause","vocab.play":"Wiedergabe","vocab.power":"Power","vocab.power_off":"Ausschalten","vocab.power_on":"Einschalten","vocab.power_toggle":"Ein/Aus","vocab.rewind":"Zurückspulen","vocab.right":"Rechts","vocab.select_ok":"Auswahl/OK","vocab.source_input":"Quelle/Eingang","vocab.speed_down":"Geschwindigkeit -","vocab.speed_up":"Geschwindigkeit +","vocab.stop":"Stopp","vocab.swing_toggle":"Lamellen schwenken","vocab.timer":"Timer","vocab.up":"Hoch","vocab.volume_down":"Lautstärke -","vocab.volume_up":"Lautstärke +"},en:_e,es:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'. Config flow (translations/es.json) was contributed separately by @Waterbrain, who would be a natural reviewer here too.","panel.loading":"Cargando…","panel.load_failed":"Error al cargar los dispositivos: {message}","panel.open_menu":"Abrir menú","panel.tab.devices":"Dispositivos","panel.tagline.devices":"Gestiona tus dispositivos IR y el hardware que los controla.","panel.tagline.sniffer":"Captura códigos IR en vivo desde el aire.","panel.tagline.clips":"Crea mandos pegando códigos IR conocidos.","panel.tagline.plucker":"Extrae códigos IR de tus emisores existentes.","panel.tagline.mirror":"Observa en vivo las transmisiones infrarrojas de Home Assistant.","common.confirm":"Confirmar","common.cancel":"Cancelar","common.are_you_sure":"¿Estás seguro?","common.remove":"Quitar","alias.placeholder":"Alias para esta señal","alias.tag":"alias","alias.clear":"Borrar alias","alias.edit":"Haz clic para editar el alias","alias.name":"Haz clic para nombrar esta señal","picker.emitters_label":"Emisores IR","picker.add_emitter":"+ Añadir emisor...","picker.no_emitters":"No se encontraron emisores IR.","picker.all_emitters_selected":"Todos los emisores están seleccionados.","picker.receivers_label":"Vía receptor(es):","picker.add_receiver":"+ Añadir receptor...","picker.no_receivers":"No se encontraron receptores IR.","picker.all_receivers_selected":"Todos los receptores están seleccionados.","device_type.media_player":"Reproductor multimedia","device_type.ac":"Aire acondicionado","device_type.fan":"Ventilador","device_type.light":"Luz","device_type.switch":"Interruptor","device_type.screen":"Pantalla / Persiana","device_type.other":"Otro","common.name":"Nombre","common.device_type":"Tipo de dispositivo","common.name_required":"El nombre es obligatorio.","common.creating":"Creando...","common.device_name_placeholder":"ej. TV del salón","promote.heading":"Promover a dispositivo","promote.device_name":"Nombre del dispositivo","promote.device_name_required":"El nombre del dispositivo es obligatorio.","promote.emitter_required":"Selecciona al menos un emisor IR.","promote.create_device":"Crear dispositivo","adddev.heading":"Añadir dispositivo","adddev.emitter_required":"Elige al menos un emisor IR.","adddev.create":"Crear","dup.heading":"Duplicar dispositivo","dup.hint_duplicating":"Duplicando {name}.","dup.hint_body":"El nuevo dispositivo recibe una copia de cada comando, asignación de acción y asignación de emisor. Puedes cambiar lo que quieras después.","dup.duplicating":"Duplicando...","dup.duplicate":"Duplicar","promote.description":"Crea un nuevo dispositivo HAIR. Después podrás asignarle señales capturadas como comandos.","capture.listening":"Esperando señal IR…","capture.instruction":'Apunta tu mando al receptor IR y pulsa el botón "{name}".',"capture.remaining":"{seconds}s restantes","capture.captured":"¡Señal capturada!","capture.protocol":"Protocolo: {protocol}","capture.protocol_raw":"Bruto","capture.verify":"¿Funcionó? Pulsa Probar para verificar.","capture.test":"▶ Probar","capture.recapture":"↻ Recapturar","capture.save_next":"Guardar y aprender siguiente ▶▶","capture.no_signal":"⚠ No se detectó señal","capture.tip_point":"Apunta el mando directamente al receptor IR","capture.tip_closer":"Acércate (a menos de 1 metro)","capture.tip_hold":"Mantén pulsado el botón brevemente","capture.try_again":"↻ Reintentar","capture.duplicate":"⚠ Señal duplicada detectada","capture.duplicate_instruction":'Esta señal coincide con tu comando "{name}". Algunos mandos usan la misma señal para varios botones.',"capture.recapture_different":"Recapturar otra","capture.save_anyway":"Guardar de todos modos","capture.error":"⚠ Error de captura","capture.learning":'Aprendiendo: "{name}"',"test_emitter.heading":"Enviar desde","test_emitter.sending":"Enviando...","test_emitter.send":"Enviar","createremote.heading":"Crear mando","createremote.type":"Tipo","createremote.blank":"Mando en blanco","createremote.from_library":"Desde la biblioteca de códigos","createremote.model":"Modelo","createremote.select_model":"Selecciona un modelo","popover.assigned_to":"Asignado a","popover.new_assignment":"+ nueva asignación","popover.open_in_devices":"Abrir {name} en Dispositivos","popover.triggers":"Disparadores","popover.new_trigger":"+ nuevo disparador","popover.any_receiver":"Cualquier receptor","popover.n_more":"{name} + {count} más","cmdrow.rename":"Haz clic para renombrar","cmdrow.tx_raw_on":"Reproduce el Pronto capturado. Haz clic para transmitir en su lugar los tiempos de paquete decodificados y limpios.","cmdrow.tx_raw_off":"Transmite los tiempos de paquete decodificados y limpios. Haz clic para reproducir en su lugar el Pronto capturado.","cmdrow.sends_times":"Envía este comando {count} veces","cmdrow.dittos":"Añade {count} dittos NEC","cmdrow.raw_timings":"BRUTO: {count} tiempos","cmdrow.not_learned":"Aún no aprendido","cmdrow.edit_code":"Ver o editar el código","cmdrow.map_action":"Asignar acción","cmdrow.actions":"ACCIONES","cmdrow.test":"Probar","cmdrow.trigger":"Disparador","cmdrow.edit_trigger":"Editar disparador","cmdrow.create_trigger":"Crear disparador","cmdrow.delete":"Eliminar","cmdrow.learn":"Aprender","trigger.alias_tag":"alias","trigger.event":"Evento disparador","trigger.edit_heading":"Editar disparador","trigger.create_heading":"Crear disparador","trigger.mirror_hint":"Se dispara cuando esta señal llega desde fuera de Home Assistant (un mando físico u otra aplicación), nunca con los envíos de la propia casa.","trigger.name_label":"Nombre del disparador","trigger.name_placeholder":"ej. Encendido TV","trigger.min_hits":"Pulsaciones mín","trigger.min_hits_hint":"Número de pulsaciones en 5s para disparar","trigger.scope_hint":"Se dispara una vez por pulsación, sin importar cuántos receptores del alcance observen la señal.","trigger.save_failed":"Error al guardar","common.saving":"Guardando...","common.update":"Actualizar","common.create":"Crear","common.delete":"Eliminar","assign.heading":"Asignar señal","assign.hits":"{count} recepciones","assign.mode_existing":"Dispositivo existente","assign.mode_new":"Dispositivo nuevo","assign.send_times":"Número de envíos","assign.send_times_hint":"Transmite este comando esta cantidad de veces por pulsación, para dispositivos que necesitan repetición. Por defecto 1.","assign.ditto_count":"Número de dittos","assign.ditto_title":"Añade tramas de repetición tras la trama principal; algunos receptores estrictos exigen al menos una para registrar el comando.","assign.ditto_hint":"Añade tramas de repetición tras la trama principal; algunos receptores estrictos exigen al menos una para registrar el comando.","assign.assigning":"Asignando...","assign.create_assign":"Crear y asignar","assign.assign":"Asignar","assign.target_device":"Dispositivo destino","assign.no_devices":'Aún no hay dispositivos. Cambia a "Dispositivo nuevo" para crear uno.',"assign.select_device":"Selecciona un dispositivo...","assign.command_name":"Nombre del comando","assign.command_placeholder":"Escribe el nombre del comando","assign.select_command":"Selecciona un comando...","assign.custom":"Personalizado...","assign.command_required":"El nombre del comando es obligatorio.","assign.target_required":"Selecciona un dispositivo destino.","assign.failed_duplicate":"Error al asignar. Puede que la señal tenga un código duplicado en el dispositivo destino.","pluckdlg.blaster_required":"Elige un emisor del que extraer.","pluckdlg.appliance_required":"El equipo es obligatorio.","pluckdlg.add_heading":"Añadir emisor","pluckdlg.loading_blasters":"Cargando emisores...","pluckdlg.pluck_from":"Extraer de","pluckdlg.select_blaster":"Selecciona un emisor","pluckdlg.appliance":"Equipo","pluckdlg.appliance_placeholder":"ej. velas","pluckdlg.name_placeholder":"ej. Velas del salón","pluckdlg.signal_heading":"Extraer señal","pluckdlg.pluck_failed":"Error al extraer.","pluckdlg.no_response":"Sin respuesta del emisor. Inténtalo de nuevo.","pluckdlg.recognized_as":"Reconocido como {protocol}","pluckdlg.valid_pronto":"Código Pronto válido","pluckdlg.command_help":"El nombre que le diste a este código cuando lo aprendiste en la app del fabricante.","pluckdlg.command_placeholder":"ej. pwr_on","pluckdlg.plucking":"Extrayendo...","pluckdlg.pluck":"Extraer","pluckdlg.captured":"Capturado","pluckdlg.remove_capture":"Quitar esta captura","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"No se encontraron emisores compatibles. Instala una integración IR compatible (como Tuya Local) y aprende primero un código.","editor.ditto_disabled_cmd":"El número de dittos se aplica cuando el comando se transmite como NEC. Cambia la píldora a NEC para activarlo.","editor.ditto_disabled":"El número de dittos se aplica a señales decodificadas (NEC hoy). Los códigos Pronto en bruto se transmiten tal como se capturaron.","editor.copied":"Copiado","editor.press_copy":"Pulsa Cmd/Ctrl+C","editor.valid":"Código Pronto válido","editor.not_valid":"Aún no es válido","editor.burst_pair.one":"{count} par de ráfagas","editor.burst_pair.other":"{count} pares de ráfagas","editor.recognized_as":"Reconocido como {protocol}","editor.snap_notice":"La portadora está a {khz} kHz, fuera de los estándares IR. Algunos receptores la rechazan.","editor.snapping":"Ajustando...","editor.snap_to":"Ajustar a {khz} kHz","editor.edit_command":"Editar comando","editor.edit_signal":"Editar señal","editor.create_signal":"Crear señal","common.save":"Guardar","editor.trigger_note_cmd":"Este comando tiene un disparador que se reapuntará automáticamente.","editor.trigger_note_sig":"Esta señal tiene un disparador que se reapuntará automáticamente.","editor.alias_label":"Alias","editor.alias_optional":"Alias (opcional)","editor.pronto_code":"Código Pronto","editor.select_all":"Seleccionar todo (luego Cmd/Ctrl+C)","editor.alias_placeholder":"ej. Encendido","editor.send_times_title":"Transmite el comando completo esta cantidad de veces como pulsaciones independientes, para dispositivos que necesitan repetición.","editor.ditto_title":"Añade tramas de repetición tras la trama principal. Algunos receptores estrictos, sobre todo equipos de audio profesionales, exigen al menos una para registrar el comando.","editor.observed.one":"Observado en la captura: {count} ditto","editor.observed.other":"Observado en la captura: {count} dittos","rel.just_now":"ahora mismo","mirror.via":"vía {name}","mirror.via_n":"vía {count} emisores","mirror.not_heard":"no escuchada","mirror.heard_in":"escuchada por última vez en {areas}","mirror.heard_by":"escuchada por última vez por {names}","mirror.chip_automation":"Envío de automatización","mirror.chip_integration":"Envío de integración","mirror.chip_test":"Envío de prueba manual","mirror.chip_device":"Dispositivo HAIR","mirror.chip_send":"Envío","mirror.unknown_title":"Señal IR desconocida enviada","mirror.unknown_hint":"{name} disparó, pero nada estaba lo bastante cerca para escuchar lo que dijo. Coloca un receptor al alcance para captar el próximo envío.","mirror.the_blaster":"El emisor","mirror.sent":"¡Enviado!","mirror.sent_all_n":"¡Enviado! ({sent}/{total})","mirror.sent_partial":"Enviado ({sent}/{total})","mirror.failed":"Fallo","mirror.error":"Error","mirror.sending":"Enviando...","mirror.test":"Probar","mirror.stat_sends":"ENVÍOS","mirror.stat_not_heard":"NO ESCUCHADAS","mirror.stat_emitters":"EMISORES","mirror.stat_signals":"SEÑALES","mirror.last_send_ago":"último envío hace {rel}","mirror.last_send_just":"último envío ahora mismo","mirror.no_receivers":"sin receptores","mirror.filter_all":"Todas ({count})","mirror.filter_not_heard":"No escuchadas ({count})","mirror.search":"Buscar envíos...","mirror.no_match":"Ningún envío coincide.","mirror.signals.one":"{count} señal","mirror.signals.other":"{count} señales","mirror.sends_times":"Envía esta señal {count} veces","mirror.assign_disabled":"Identidad desconocida -- no se escuchó nada de vuelta que asignar","mirror.assigned_one":"Asignada a {device} / {command}","mirror.assigned_n":"Asignada a {count} comandos:","mirror.assign_title":"Asignar esta señal a un dispositivo HAIR","mirror.test_title":"Enviar esta señal por un emisor para probarla","mirror.test_disabled":"Identidad desconocida -- nada que enviar","mirror.trigger_disabled":"Identidad desconocida -- nada que vincular","mirror.trigger_edit":"Editar disparador(es) de esta señal","mirror.trigger_create":"Se dispara cuando esta señal llega desde fuera de Home Assistant","mirror.delete_title":"Borrar esta entrada (vuelve con el próximo envío)","mirror.empty_title":"Aún no se ha enviado nada","mirror.empty_sub":"Los comandos enviados por dispositivos HAIR, automatizaciones o cualquier integración de la plataforma infrarroja aparecerán aquí, con su destino y quién los escuchó.","mirror.del_trigger_title":"Eliminar disparador","mirror.del_trigger_msg":"¿Eliminar este disparador permanentemente? Las automatizaciones que lo usan dejarán de dispararse.","mirror.clear_title":"Borrar entrada del Mirror","mirror.clear_msg":"¿Quitar esta entrada del Mirror? Volverá la próxima vez que se envíe esta señal.","common.delete_failed":"Error al eliminar: {message}","device_type.other_card":"Dispositivo IR","devlist.loading":"Cargando dispositivos IR...","devlist.empty_title":"Aún no hay dispositivos IR","devlist.empty_sub":"Añade tu primer dispositivo para empezar.","devlist.add_device_plus":"+ Añadir dispositivo","devlist.title":"Dispositivos HAIR","devlist.add_device":"Añadir dispositivo","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Sin TX","devlist.rx_native_title":"Recibe vía la plataforma infrarroja nativa de HA","devlist.rx_bridge_active":"El puente heredado sigue activo. El receptor nativo lo reemplaza -- puedes quitar el bloque on_pronto: de tu configuración ESPHome.","devlist.rx_bridge_title":"Recibe vía el puente heredado de eventos ESPHome","devlist.rx_upgrade_title":"Actualiza a HA 2026.6+ para soporte nativo de receptores","devlist.tx_native_title":"Envía vía la plataforma infrarroja nativa de HA","devlist.blasters":"Emisores (extraíbles)","devlist.emitters":"Emisores","devlist.receivers":"Receptores","devlist.proxies":"Proxies","devlist.hits_badge":"{count}x recepciones","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Eliminar disparador","devlist.delete_device":"Eliminar dispositivo","devlist.open_plucker_title":"Abrir en el Plucker","devlist.open_plucker":"Abrir en el Plucker","devlist.del_trigger_msg":'¿Quitar "{name}"? La entidad de evento HA asociada también se eliminará.',"devlist.del_device_title":"Eliminar dispositivo","devlist.del_device_msg":'¿Quitar "{name}"? Se eliminarán los comandos, asignaciones de acción y asignaciones de emisor. Los disparadores no se ven afectados.',"common.close":"Cerrar","devdetail.name_updated":"Nombre actualizado","devdetail.type_updated":"Tipo de dispositivo actualizado","devdetail.emitters_updated":"Emisores actualizados","devdetail.update_failed":"Error al actualizar: {message}","devdetail.reorder_failed":"Error al reordenar: {message}","devdetail.mapped_to":"Asignado a {action}","devdetail.mapping_cleared":"Asignación borrada","devdetail.mapping_failed":"Error en la asignación: {message}","devdetail.sent_cmd":'"{name}" enviado',"devdetail.send_failed":"Error al enviar: {message}","devdetail.cmd_updated":"Comando actualizado","devdetail.cmd_updated_repointed":"Comando actualizado. Disparador {names} reapuntado.","devdetail.rename_failed":"Error al renombrar: {message}","devdetail.removed":'"{name}" eliminado',"devdetail.saved":'"{name}" guardado',"devdetail.type":"Tipo","devdetail.commands":"Comandos ({count})","devdetail.no_commands":"Aún no hay comandos. Añade uno abajo.","devdetail.drag":"Arrastra para reordenar","devdetail.map_action":"Asignar acción","devdetail.none_clear":"Ninguna (borrar)","devdetail.sniff_title":"Capturar una nueva señal en el Sniffer","devdetail.sniffed":"+ Señal olfateada","devdetail.clip_title":"Pegar una nueva señal en Clips","devdetail.clipped":"+ Señal pegada","devdetail.mirror_title":"Escuchar un envío en el Mirror","devdetail.mirrored":"+ Señal del Mirror","devdetail.del_device_title":"¿Eliminar {name}?","devdetail.del_device_msg":"Esto elimina todos los comandos capturados y la entidad creada automáticamente. Esta acción no se puede deshacer.","devdetail.del_cmd_title":"¿Eliminar comando?","devdetail.del_cmd_msg":'¿Quitar "{name}"? No se puede deshacer.',"devdetail.del_trigger_msg":"¿Quitar este disparador? La entidad de evento HA asociada también se eliminará.","rel.min_ago":"hace {count} min","rel.h_ago":"hace {count}h","rel.d_ago":"hace {count}d","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} mando","sniffer.remotes.other":"{count} mandos","sniffer.scanning":"Buscando señales...","sniffer.empty_title":"No se detectaron señales desconocidas","sniffer.empty_body":"Cuando tus dispositivos ESPHome reciban señales IR no reconocidas, aparecerán aquí automáticamente.","sniffer.empty_hint":"Prueba a pulsar un botón de un mando que aún no esté configurado.","sniffer.norx_title":"No hay ningún receptor IR configurado","sniffer.norx_body":"HAIR aún no tiene forma de recibir señales IR, así que el Sniffer no puede capturar nada.","sniffer.norx_hint":"Configura un receptor ESPHome con la plataforma infrarroja, o revisa Ajustes, luego Dispositivos y servicios, para confirmar que tu dispositivo IR está adoptado.","sniffer.show_dismissed_title":"Restaurar mandos ocultados anteriormente","sniffer.show_dismissed":"Mostrar descartados","sniffer.hide_dismissed":"Ocultar descartados","sniffer.clear_all_title":"Borra todo el catálogo de desconocidos Y la lista de descartados. Usa Mostrar descartados antes de Borrar todo si quieres conservar entradas descartadas individuales.","sniffer.clear_all":"Borrar todo","sniffer.del_signal_title":"Eliminar señal","sniffer.del_signal_msg":"¿Eliminar esta señal permanentemente? No se puede deshacer.","sniffer.clear_all_confirm_title":"Borrar todas las señales","sniffer.clear_all_confirm_msg":"¿Quitar todas las señales y dispositivos desconocidos? No se puede deshacer.","sniffer.hair_device":"Dispositivo HAIR","sniffer.promote":"Promover","sniffer.dismissed":"descartado","sniffer.restore":"Restaurar","sniffer.dismiss":"Descartar","sniffer.addr":"dir: {address}","sniffer.signals_head":"Señales ({count})","sniffer.first_seen":"Vista por primera vez: {time}","sniffer.restore_first":"Restaura primero este mando","sniffer.trigger_create":"Crear una entidad de evento HA que se dispare con esta señal","common.raw":"BRUTO","sniffer.hit_word.one":"recepción","sniffer.hit_word.other":"recepciones","sniffer.signal_word.one":"señal","sniffer.signal_word.other":"señales","common.loading_plain":"Cargando...","clips.title":"HAIR Clipper","clips.add_remote":"+ Añadir mando","clips.empty_title":"Aún no hay mandos virtuales","clips.empty_body":"Clipper te permite crear mandos pegando códigos Pronto. Crea un mando y luego añade una señal por cada botón.","clips.empty_hint":'Haz clic en "+ Añadir mando" arriba para empezar un mando pegado.',"clips.clear_all_title":"Elimina todos los mandos pegados y sus señales. Las señales olfateadas no se tocan.","clips.remote_fallback":"Mando","clips.add_signal_title":"Añadir una señal a este mando","clips.add_signal":"+ Añadir señal","clips.no_signals":'Aún no hay señales. Haz clic en "+ Añadir señal" para pegar un código Pronto.',"clips.delete_remote_title":"Eliminar este mando y todas sus señales","clips.delete_remote":"Eliminar mando","clips.test_title":"Enviar esta señal por un emisor","clips.clear_all_confirm_title":"Borrar todos los clips","clips.clear_all_confirm_msg":"¿Quitar todos los mandos pegados y sus señales? No se puede deshacer. Las señales olfateadas no se ven afectadas.","clips.del_remote_confirm_title":"Eliminar mando","clips.del_remote_msg_n.one":'¿Quitar "{name}" y su {count} señal? No se puede deshacer.',"clips.del_remote_msg_n.other":'¿Quitar "{name}" y sus {count} señales? No se puede deshacer.',"clips.del_remote_msg":'¿Quitar "{name}"? No se puede deshacer.',"pluck.vendor_unavailable":"La integración de este emisor no está disponible ahora mismo. Asegúrate de que la integración del fabricante está cargada.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Añadir emisor","pluck.empty_title":"Aún no hay emisores extraídos","pluck.empty_body":"El Plucker importa códigos IR de tus emisores existentes para usarlos en HAIR sin volver a aprender cada uno.","pluck.empty_hint":'Haz clic en "+ Añadir emisor" arriba para reflejar un emisor.',"pluck.clear_all_title":"Elimina todos los emisores extraídos y sus señales. Las señales olfateadas y pegadas no se tocan.","pluck.blaster_fallback":"Emisor","pluck.promote_title":"Crear un dispositivo HAIR desde este emisor","pluck.pluck_signal_title":"Extraer un código de este emisor","pluck.pluck_signal":"+ Extraer señal","pluck.no_signals":'Aún no hay señales. Haz clic en "+ Extraer señal" para sacar un código de este emisor.',"pluck.delete_blaster_title":"Eliminar este emisor y todas sus señales","pluck.delete_blaster":"Eliminar emisor","pluck.clear_all_confirm_title":"Borrar todo lo extraído","pluck.clear_all_confirm_msg":"¿Quitar todos los emisores extraídos y sus señales? No se puede deshacer. Las señales olfateadas y pegadas no se ven afectadas.","pluck.del_blaster_confirm_title":"Eliminar emisor","devdetail.custom_action":"Personalizado...","devdetail.custom_action_placeholder":"ej. temp_30","devdetail.set":"Fijar","vocab.back_return":"Atrás","vocab.brightness_down":"Brillo -","vocab.brightness_up":"Brillo +","vocab.channel_down":"Canal -","vocab.channel_up":"Canal +","vocab.close":"Cerrar","vocab.color_temp_cooler":"Blanco más frío","vocab.color_temp_warmer":"Blanco más cálido","vocab.down":"Abajo","vocab.fan_auto":"Ventilador: Auto","vocab.fan_high":"Ventilador: Alto","vocab.fan_low":"Ventilador: Bajo","vocab.fan_medium":"Ventilador: Medio","vocab.fast_forward":"Avance rápido","vocab.guide":"Guía","vocab.left":"Izquierda","vocab.menu":"Menú","vocab.mode_auto":"Modo: Auto","vocab.mode_cool":"Modo: Frío","vocab.mode_dry":"Modo: Seco","vocab.mode_fan":"Modo: Ventilador","vocab.mode_heat":"Modo: Calor","vocab.mute":"Silencio","vocab.off":"Apagado","vocab.on":"Encendido","vocab.open":"Abrir","vocab.oscillate":"Oscilar","vocab.pause":"Pausa","vocab.play":"Reproducir","vocab.power":"Alimentación","vocab.power_off":"Apagar","vocab.power_on":"Encender","vocab.power_toggle":"Alternar encendido","vocab.rewind":"Rebobinar","vocab.right":"Derecha","vocab.select_ok":"Seleccionar/OK","vocab.source_input":"Fuente/Entrada","vocab.speed_down":"Velocidad -","vocab.speed_up":"Velocidad +","vocab.stop":"Detener","vocab.swing_toggle":"Oscilación de aletas","vocab.timer":"Temporizador","vocab.up":"Arriba","vocab.volume_down":"Volumen -","vocab.volume_up":"Volumen +"},fr:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Chargement…","panel.load_failed":"Échec du chargement des appareils : {message}","panel.open_menu":"Ouvrir le menu","panel.tab.devices":"Appareils","panel.tagline.devices":"Gérez vos appareils IR et le matériel qui les pilote.","panel.tagline.sniffer":"Capturez des codes IR en direct dans l'air.","panel.tagline.clips":"Créez des télécommandes en collant des codes IR connus.","panel.tagline.plucker":"Cueillez des codes IR depuis vos blasters existants.","panel.tagline.mirror":"Visualisez en direct les transmissions infrarouges de Home Assistant.","common.confirm":"Confirmer","common.cancel":"Annuler","common.are_you_sure":"Êtes-vous sûr ?","common.remove":"Retirer","alias.placeholder":"Alias pour ce signal","alias.tag":"alias","alias.clear":"Effacer l'alias","alias.edit":"Cliquez pour modifier l'alias","alias.name":"Cliquez pour nommer ce signal","picker.emitters_label":"Émetteurs IR","picker.add_emitter":"+ Ajouter un émetteur...","picker.no_emitters":"Aucun émetteur IR trouvé.","picker.all_emitters_selected":"Tous les émetteurs sont sélectionnés.","picker.receivers_label":"Via récepteur(s) :","picker.add_receiver":"+ Ajouter un récepteur...","picker.no_receivers":"Aucun récepteur IR trouvé.","picker.all_receivers_selected":"Tous les récepteurs sont sélectionnés.","device_type.media_player":"Lecteur multimédia","device_type.ac":"Climatiseur","device_type.fan":"Ventilateur","device_type.light":"Lumière","device_type.switch":"Interrupteur","device_type.screen":"Écran / Store","device_type.other":"Autre","common.name":"Nom","common.device_type":"Type d'appareil","common.name_required":"Le nom est requis.","common.creating":"Création...","common.device_name_placeholder":"ex. TV du salon","promote.heading":"Promouvoir en appareil","promote.device_name":"Nom de l'appareil","promote.device_name_required":"Le nom de l'appareil est requis.","promote.emitter_required":"Sélectionnez au moins un émetteur IR.","promote.create_device":"Créer l'appareil","adddev.heading":"Ajouter un appareil","adddev.emitter_required":"Choisissez au moins un émetteur IR.","adddev.create":"Créer","dup.heading":"Dupliquer l'appareil","dup.hint_duplicating":"Duplication de {name}.","dup.hint_body":"Le nouvel appareil reçoit une copie de chaque commande, mappage d'action et assignation d'émetteur. Vous pourrez tout modifier ensuite.","dup.duplicating":"Duplication...","dup.duplicate":"Dupliquer","promote.description":"Créez un nouvel appareil HAIR. Vous pourrez ensuite lui assigner des signaux capturés comme commandes.","capture.listening":"En écoute d'un signal IR…","capture.instruction":'Pointez votre télécommande vers le récepteur IR et appuyez sur le bouton "{name}".',"capture.remaining":"{seconds}s restantes","capture.captured":"Signal capturé !","capture.protocol":"Protocole : {protocol}","capture.protocol_raw":"Brut","capture.verify":"Ça a fonctionné ? Appuyez sur Test pour vérifier.","capture.test":"▶ Test","capture.recapture":"↻ Recapturer","capture.save_next":"Enregistrer et apprendre le suivant ▶▶","capture.no_signal":"⚠ Aucun signal détecté","capture.tip_point":"Pointez la télécommande directement vers le récepteur IR","capture.tip_closer":"Rapprochez-vous (à moins de 1 mètre)","capture.tip_hold":"Appuyez brièvement sur le bouton en le maintenant","capture.try_again":"↻ Réessayer","capture.duplicate":"⚠ Signal en double détecté","capture.duplicate_instruction":'Ce signal correspond à votre commande "{name}". Certaines télécommandes utilisent le même signal pour plusieurs boutons.',"capture.recapture_different":"Recapturer un autre","capture.save_anyway":"Enregistrer quand même","capture.error":"⚠ Erreur de capture","capture.learning":'Apprentissage : "{name}"',"test_emitter.heading":"Envoyer depuis","test_emitter.sending":"Envoi...","test_emitter.send":"Envoyer","createremote.heading":"Créer une télécommande","createremote.type":"Type","createremote.blank":"Télécommande vierge","createremote.from_library":"Depuis la bibliothèque de codes","createremote.model":"Modèle","createremote.select_model":"Sélectionnez un modèle","popover.assigned_to":"Assigné à","popover.new_assignment":"+ nouvelle assignation","popover.open_in_devices":"Ouvrir {name} dans Appareils","popover.triggers":"Déclencheurs","popover.new_trigger":"+ nouveau déclencheur","popover.any_receiver":"N'importe quel récepteur","popover.n_more":"{name} + {count} autres","cmdrow.rename":"Cliquez pour renommer","cmdrow.tx_raw_on":"Rejoue le Pronto capturé. Cliquez pour transmettre à la place les timings de paquet décodés propres.","cmdrow.tx_raw_off":"Transmet les timings de paquet décodés propres. Cliquez pour rejouer à la place le Pronto capturé.","cmdrow.sends_times":"Envoie cette commande {count} fois","cmdrow.dittos":"Ajoute {count} dittos NEC","cmdrow.raw_timings":"BRUT : {count} timings","cmdrow.not_learned":"Pas encore appris","cmdrow.edit_code":"Voir ou modifier le code","cmdrow.map_action":"Assigner un mappage d'action","cmdrow.actions":"ACTIONS","cmdrow.test":"Test","cmdrow.trigger":"Déclencheur","cmdrow.edit_trigger":"Modifier le déclencheur","cmdrow.create_trigger":"Créer un déclencheur","cmdrow.delete":"Supprimer","cmdrow.learn":"Apprendre","trigger.alias_tag":"alias","trigger.event":"Événement déclencheur","trigger.edit_heading":"Modifier le déclencheur","trigger.create_heading":"Créer un déclencheur","trigger.mirror_hint":"Se déclenche quand ce signal arrive de l'extérieur de Home Assistant (une télécommande physique ou une autre application), jamais sur les envois de la maison elle-même.","trigger.name_label":"Nom du déclencheur","trigger.name_placeholder":"ex. Alimentation TV","trigger.min_hits":"Appuis min","trigger.min_hits_hint":"Nombre d'appuis en 5s pour déclencher","trigger.scope_hint":"Se déclenche une fois par appui, quel que soit le nombre de récepteurs concernés qui observent le signal.","trigger.save_failed":"Échec de l'enregistrement","common.saving":"Enregistrement...","common.update":"Mettre à jour","common.create":"Créer","common.delete":"Supprimer","assign.heading":"Assigner le signal","assign.hits":"{count} réceptions","assign.mode_existing":"Appareil existant","assign.mode_new":"Nouvel appareil","assign.send_times":"Nombre d'envois","assign.send_times_hint":"Transmet cette commande autant de fois par appui, pour les appareils qui ont besoin d'une répétition. Par défaut 1.","assign.ditto_count":"Nombre de dittos","assign.ditto_title":"Ajoute des trames de répétition après la trame principale ; certains récepteurs stricts en exigent au moins une pour enregistrer la commande.","assign.ditto_hint":"Ajoute des trames de répétition après la trame principale ; certains récepteurs stricts en exigent au moins une pour enregistrer la commande.","assign.assigning":"Assignation...","assign.create_assign":"Créer et assigner","assign.assign":"Assigner","assign.target_device":"Appareil cible","assign.no_devices":'Aucun appareil pour l\'instant. Passez à "Nouvel appareil" pour en créer un.',"assign.select_device":"Sélectionnez un appareil...","assign.command_name":"Nom de la commande","assign.command_placeholder":"Saisissez le nom de la commande","assign.select_command":"Sélectionnez une commande...","assign.custom":"Personnalisé...","assign.command_required":"Le nom de la commande est requis.","assign.target_required":"Sélectionnez un appareil cible.","assign.failed_duplicate":"Échec de l'assignation. Le signal a peut-être un code en double sur l'appareil cible.","pluckdlg.blaster_required":"Choisissez un blaster à cueillir.","pluckdlg.appliance_required":"L'équipement est requis.","pluckdlg.add_heading":"Ajouter un blaster","pluckdlg.loading_blasters":"Chargement des blasters...","pluckdlg.pluck_from":"Cueillir depuis","pluckdlg.select_blaster":"Sélectionnez un blaster","pluckdlg.appliance":"Équipement","pluckdlg.appliance_placeholder":"ex. bougies","pluckdlg.name_placeholder":"ex. Bougies du salon","pluckdlg.signal_heading":"Cueillir un signal","pluckdlg.pluck_failed":"Échec de la cueillette.","pluckdlg.no_response":"Pas de réponse du blaster. Réessayez.","pluckdlg.recognized_as":"Reconnu comme {protocol}","pluckdlg.valid_pronto":"Code Pronto valide","pluckdlg.command_help":"Le nom que vous avez donné à ce code lors de son apprentissage dans l'application du fabricant.","pluckdlg.command_placeholder":"ex. pwr_on","pluckdlg.plucking":"Cueillette...","pluckdlg.pluck":"Cueillir","pluckdlg.captured":"Capturé","pluckdlg.remove_capture":"Retirer cette capture","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Aucun blaster compatible trouvé. Installez une intégration IR prise en charge (comme Tuya Local) et apprenez d'abord un code.","editor.ditto_disabled_cmd":"Le nombre de dittos s'applique quand la commande est transmise en NEC. Basculez la pastille sur NEC pour l'activer.","editor.ditto_disabled":"Le nombre de dittos s'applique aux signaux décodés (NEC aujourd'hui). Les codes Pronto bruts sont transmis tels que capturés.","editor.copied":"Copié","editor.press_copy":"Appuyez sur Cmd/Ctrl+C","editor.valid":"Code Pronto valide","editor.not_valid":"Pas encore valide","editor.burst_pair.one":"{count} paire de rafales","editor.burst_pair.other":"{count} paires de rafales","editor.recognized_as":"Reconnu comme {protocol}","editor.snap_notice":"La porteuse est à {khz} kHz, hors des standards IR. Certains récepteurs la rejettent.","editor.snapping":"Ajustement...","editor.snap_to":"Ajuster à {khz} kHz","editor.edit_command":"Modifier la commande","editor.edit_signal":"Modifier le signal","editor.create_signal":"Créer un signal","common.save":"Enregistrer","editor.trigger_note_cmd":"Cette commande a un déclencheur qui se re-pointera automatiquement.","editor.trigger_note_sig":"Ce signal a un déclencheur qui se re-pointera automatiquement.","editor.alias_label":"Alias","editor.alias_optional":"Alias (facultatif)","editor.pronto_code":"Code Pronto","editor.select_all":"Tout sélectionner (puis Cmd/Ctrl+C)","editor.alias_placeholder":"ex. Alimentation","editor.send_times_title":"Transmet la commande entière autant de fois comme des appuis indépendants, pour les appareils qui ont besoin d'une répétition.","editor.ditto_title":"Ajoute des trames de répétition après la trame principale. Certains récepteurs stricts, notamment le matériel audio professionnel, en exigent au moins une pour enregistrer la commande.","editor.observed.one":"Observé à la capture : {count} ditto","editor.observed.other":"Observé à la capture : {count} dittos","rel.just_now":"à l'instant","mirror.via":"via {name}","mirror.via_n":"via {count} émetteurs","mirror.not_heard":"pas entendu","mirror.heard_in":"entendu pour la dernière fois dans {areas}","mirror.heard_by":"entendu pour la dernière fois par {names}","mirror.chip_automation":"Envoi d'automatisation","mirror.chip_integration":"Envoi d'intégration","mirror.chip_test":"Envoi de test manuel","mirror.chip_device":"Appareil HAIR","mirror.chip_send":"Envoi","mirror.unknown_title":"Signal IR inconnu envoyé","mirror.unknown_hint":"{name} a émis, mais rien n'était assez proche pour entendre ce qu'il a dit. Placez un récepteur à portée d'oreille pour capter le prochain envoi.","mirror.the_blaster":"Le blaster","mirror.sent":"Envoyé !","mirror.sent_all_n":"Envoyé ! ({sent}/{total})","mirror.sent_partial":"Envoyé ({sent}/{total})","mirror.failed":"Échec","mirror.error":"Erreur","mirror.sending":"Envoi...","mirror.test":"Test","mirror.stat_sends":"ENVOIS","mirror.stat_not_heard":"PAS ENTENDUS","mirror.stat_emitters":"ÉMETTEURS","mirror.stat_signals":"SIGNAUX","mirror.last_send_ago":"dernier envoi il y a {rel}","mirror.last_send_just":"dernier envoi à l'instant","mirror.no_receivers":"aucun récepteur","mirror.filter_all":"Tous ({count})","mirror.filter_not_heard":"Pas entendus ({count})","mirror.search":"Rechercher des envois...","mirror.no_match":"Aucun envoi ne correspond.","mirror.signals.one":"{count} signal","mirror.signals.other":"{count} signaux","mirror.sends_times":"Envoie ce signal {count} fois","mirror.assign_disabled":"Identité inconnue -- rien n'a été entendu en retour à assigner","mirror.assigned_one":"Assigné à {device} / {command}","mirror.assigned_n":"Assigné à {count} commandes :","mirror.assign_title":"Assigner ce signal à un appareil HAIR","mirror.test_title":"Envoyer ce signal via un émetteur pour le tester","mirror.test_disabled":"Identité inconnue -- rien à envoyer","mirror.trigger_disabled":"Identité inconnue -- rien à lier","mirror.trigger_edit":"Modifier le(s) déclencheur(s) de ce signal","mirror.trigger_create":"Se déclenche quand ce signal arrive de l'extérieur de Home Assistant","mirror.delete_title":"Effacer cette entrée (elle revient au prochain envoi)","mirror.empty_title":"Rien d'envoyé pour l'instant","mirror.empty_sub":"Les commandes envoyées par les appareils HAIR, les automatisations ou toute intégration de la plateforme infrarouge apparaîtront ici, avec leur destination et qui les a entendues.","mirror.del_trigger_title":"Supprimer le déclencheur","mirror.del_trigger_msg":"Supprimer définitivement ce déclencheur ? Les automatisations qui l'utilisent cesseront de se déclencher.","mirror.clear_title":"Effacer l'entrée du Mirror","mirror.clear_msg":"Retirer cette entrée du Mirror ? Elle reviendra au prochain envoi de ce signal.","common.delete_failed":"Échec de la suppression : {message}","device_type.other_card":"Appareil IR","devlist.loading":"Chargement des appareils IR...","devlist.empty_title":"Aucun appareil IR pour l'instant","devlist.empty_sub":"Ajoutez votre premier appareil pour commencer.","devlist.add_device_plus":"+ Ajouter un appareil","devlist.title":"Appareils HAIR","devlist.add_device":"Ajouter un appareil","devlist.cmd_badge":"CMD : {count}","devlist.tx_badge":"TX : {count}","devlist.no_tx":"Pas de TX","devlist.rx_native_title":"Reçoit via la plateforme infrarouge native de HA","devlist.rx_bridge_active":"Le pont hérité est toujours actif. Le récepteur natif le remplace -- vous pouvez retirer le bloc on_pronto: de votre configuration ESPHome.","devlist.rx_bridge_title":"Reçoit via l'ancien pont d'événements ESPHome","devlist.rx_upgrade_title":"Passez à HA 2026.6+ pour la prise en charge native des récepteurs","devlist.tx_native_title":"Envoie via la plateforme infrarouge native de HA","devlist.blasters":"Blasters (cueillables)","devlist.emitters":"Émetteurs","devlist.receivers":"Récepteurs","devlist.proxies":"Proxys","devlist.hits_badge":"{count}x réceptions","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Supprimer le déclencheur","devlist.delete_device":"Supprimer l'appareil","devlist.open_plucker_title":"Ouvrir dans le Plucker","devlist.open_plucker":"Ouvrir dans le Plucker","devlist.del_trigger_msg":"Retirer \"{name}\" ? L'entité d'événement HA associée sera aussi supprimée.","devlist.del_device_title":"Supprimer l'appareil","devlist.del_device_msg":"Retirer \"{name}\" ? Les commandes, mappages d'action et assignations d'émetteur seront supprimés. Les déclencheurs ne sont pas affectés.","common.close":"Fermer","devdetail.name_updated":"Nom mis à jour","devdetail.type_updated":"Type d'appareil mis à jour","devdetail.emitters_updated":"Émetteurs mis à jour","devdetail.update_failed":"Échec de la mise à jour : {message}","devdetail.reorder_failed":"Échec du réordonnancement : {message}","devdetail.mapped_to":"Mappé sur {action}","devdetail.mapping_cleared":"Mappage effacé","devdetail.mapping_failed":"Échec du mappage : {message}","devdetail.sent_cmd":'"{name}" envoyé',"devdetail.send_failed":"Échec de l'envoi : {message}","devdetail.cmd_updated":"Commande mise à jour","devdetail.cmd_updated_repointed":"Commande mise à jour. Déclencheur {names} re-pointé.","devdetail.rename_failed":"Échec du renommage : {message}","devdetail.removed":'"{name}" retiré',"devdetail.saved":'"{name}" enregistré',"devdetail.type":"Type","devdetail.commands":"Commandes ({count})","devdetail.no_commands":"Aucune commande pour l'instant. Ajoutez-en une ci-dessous.","devdetail.drag":"Glissez pour réordonner","devdetail.map_action":"Mapper une action","devdetail.none_clear":"Aucune (effacer)","devdetail.sniff_title":"Capturer un nouveau signal dans le Sniffer","devdetail.sniffed":"+ Signal sniffé","devdetail.clip_title":"Coller un nouveau signal dans Clips","devdetail.clipped":"+ Signal collé","devdetail.mirror_title":"Surprendre un envoi dans le Mirror","devdetail.mirrored":"+ Signal du Mirror","devdetail.del_device_title":"Supprimer {name} ?","devdetail.del_device_msg":"Cela supprime toutes les commandes capturées et l'entité créée automatiquement. Cette action est irréversible.","devdetail.del_cmd_title":"Supprimer la commande ?","devdetail.del_cmd_msg":'Retirer "{name}" ? Cette action est irréversible.',"devdetail.del_trigger_msg":"Retirer ce déclencheur ? L'entité d'événement HA associée sera aussi supprimée.","rel.min_ago":"il y a {count} min","rel.h_ago":"il y a {count}h","rel.d_ago":"il y a {count}j","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} télécommande","sniffer.remotes.other":"{count} télécommandes","sniffer.scanning":"Recherche de signaux...","sniffer.empty_title":"Aucun signal inconnu détecté","sniffer.empty_body":"Quand des signaux IR non reconnus sont reçus par vos appareils ESPHome, ils apparaissent ici automatiquement.","sniffer.empty_hint":"Essayez d'appuyer sur un bouton d'une télécommande pas encore configurée.","sniffer.norx_title":"Aucun récepteur IR n'est configuré","sniffer.norx_body":"HAIR n'a encore aucun moyen de recevoir des signaux IR, le Sniffer ne peut donc rien capturer.","sniffer.norx_hint":"Configurez un récepteur ESPHome avec la plateforme infrarouge, ou vérifiez dans Paramètres, puis Appareils et services, que votre appareil IR est bien adopté.","sniffer.show_dismissed_title":"Restaurer des télécommandes précédemment ignorées","sniffer.show_dismissed":"Afficher les ignorées","sniffer.hide_dismissed":"Masquer les ignorées","sniffer.clear_all_title":"Vide tout le catalogue inconnu ET la liste des ignorés. Utilisez Afficher les ignorées avant Tout effacer si vous voulez conserver certaines entrées ignorées.","sniffer.clear_all":"Tout effacer","sniffer.del_signal_title":"Supprimer le signal","sniffer.del_signal_msg":"Supprimer définitivement ce signal ? Cette action est irréversible.","sniffer.clear_all_confirm_title":"Effacer tous les signaux","sniffer.clear_all_confirm_msg":"Supprimer tous les signaux et appareils inconnus ? Cette action est irréversible.","sniffer.hair_device":"Appareil HAIR","sniffer.promote":"Promouvoir","sniffer.dismissed":"ignorée","sniffer.restore":"Restaurer","sniffer.dismiss":"Ignorer","sniffer.addr":"adr : {address}","sniffer.signals_head":"Signaux ({count})","sniffer.first_seen":"Vu pour la première fois : {time}","sniffer.restore_first":"Restaurez d'abord cette télécommande","sniffer.trigger_create":"Créer une entité d'événement HA qui se déclenche sur ce signal","common.raw":"BRUT","sniffer.hit_word.one":"réception","sniffer.hit_word.other":"réceptions","sniffer.signal_word.one":"signal","sniffer.signal_word.other":"signaux","common.loading_plain":"Chargement...","clips.title":"HAIR Clipper","clips.add_remote":"+ Ajouter une télécommande","clips.empty_title":"Aucune télécommande virtuelle pour l'instant","clips.empty_body":"Clipper vous permet de créer des télécommandes en collant des codes Pronto. Créez une télécommande, puis ajoutez un signal pour chaque bouton.","clips.empty_hint":'Cliquez sur "+ Ajouter une télécommande" ci-dessus pour commencer une télécommande collée.',"clips.clear_all_title":"Supprime toutes les télécommandes collées et leurs signaux. Les signaux sniffés ne sont pas touchés.","clips.remote_fallback":"Télécommande","clips.add_signal_title":"Ajouter un signal à cette télécommande","clips.add_signal":"+ Ajouter un signal","clips.no_signals":'Aucun signal pour l\'instant. Cliquez sur "+ Ajouter un signal" pour coller un code Pronto.',"clips.delete_remote_title":"Supprimer cette télécommande et tous ses signaux","clips.delete_remote":"Supprimer la télécommande","clips.test_title":"Envoyer ce signal via un émetteur","clips.clear_all_confirm_title":"Effacer tous les clips","clips.clear_all_confirm_msg":"Supprimer toutes les télécommandes collées et leurs signaux ? Cette action est irréversible. Les signaux sniffés ne sont pas affectés.","clips.del_remote_confirm_title":"Supprimer la télécommande","clips.del_remote_msg_n.one":'Retirer "{name}" et son {count} signal ? Cette action est irréversible.',"clips.del_remote_msg_n.other":'Retirer "{name}" et ses {count} signaux ? Cette action est irréversible.',"clips.del_remote_msg":'Retirer "{name}" ? Cette action est irréversible.',"pluck.vendor_unavailable":"L'intégration de ce blaster n'est pas disponible pour le moment. Vérifiez que l'intégration du fabricant est chargée.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Ajouter un blaster","pluck.empty_title":"Aucun blaster cueilli pour l'instant","pluck.empty_body":"Le Plucker importe les codes IR de vos blasters existants pour les utiliser dans HAIR sans tout réapprendre.","pluck.empty_hint":'Cliquez sur "+ Ajouter un blaster" ci-dessus pour refléter un blaster.',"pluck.clear_all_title":"Supprime tous les blasters cueillis et leurs signaux. Les signaux sniffés et collés ne sont pas touchés.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Créer un appareil HAIR à partir de ce blaster","pluck.pluck_signal_title":"Cueillir un code sur ce blaster","pluck.pluck_signal":"+ Cueillir un signal","pluck.no_signals":'Aucun signal pour l\'instant. Cliquez sur "+ Cueillir un signal" pour extraire un code de ce blaster.',"pluck.delete_blaster_title":"Supprimer ce blaster et tous ses signaux","pluck.delete_blaster":"Supprimer le blaster","pluck.clear_all_confirm_title":"Effacer tous les cueillis","pluck.clear_all_confirm_msg":"Supprimer tous les blasters cueillis et leurs signaux ? Cette action est irréversible. Les signaux sniffés et collés ne sont pas affectés.","pluck.del_blaster_confirm_title":"Supprimer le blaster","devdetail.custom_action":"Personnalisé...","devdetail.custom_action_placeholder":"ex. temp_30","devdetail.set":"Définir","vocab.back_return":"Retour","vocab.brightness_down":"Luminosité -","vocab.brightness_up":"Luminosité +","vocab.channel_down":"Chaîne -","vocab.channel_up":"Chaîne +","vocab.close":"Fermer","vocab.color_temp_cooler":"Blanc plus froid","vocab.color_temp_warmer":"Blanc plus chaud","vocab.down":"Bas","vocab.fan_auto":"Ventilation : Auto","vocab.fan_high":"Ventilation : Forte","vocab.fan_low":"Ventilation : Faible","vocab.fan_medium":"Ventilation : Moyenne","vocab.fast_forward":"Avance rapide","vocab.guide":"Guide","vocab.left":"Gauche","vocab.menu":"Menu","vocab.mode_auto":"Mode : Auto","vocab.mode_cool":"Mode : Froid","vocab.mode_dry":"Mode : Déshumidification","vocab.mode_fan":"Mode : Ventilation","vocab.mode_heat":"Mode : Chauffage","vocab.mute":"Muet","vocab.off":"Arrêt","vocab.on":"Marche","vocab.open":"Ouvrir","vocab.oscillate":"Oscillation","vocab.pause":"Pause","vocab.play":"Lecture","vocab.power":"Alimentation","vocab.power_off":"Éteindre","vocab.power_on":"Allumer","vocab.power_toggle":"Marche/Arrêt","vocab.rewind":"Retour rapide","vocab.right":"Droite","vocab.select_ok":"Sélection/OK","vocab.source_input":"Source/Entrée","vocab.speed_down":"Vitesse -","vocab.speed_up":"Vitesse +","vocab.stop":"Stop","vocab.swing_toggle":"Balayage","vocab.timer":"Minuterie","vocab.up":"Haut","vocab.volume_down":"Volume -","vocab.volume_up":"Volume +"},it:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Caricamento…","panel.load_failed":"Impossibile caricare i dispositivi: {message}","panel.open_menu":"Apri menu","panel.tab.devices":"Dispositivi","panel.tagline.devices":"Gestisci i tuoi dispositivi IR e l'hardware che li comanda.","panel.tagline.sniffer":"Cattura codici IR dal vivo, direttamente dall'aria.","panel.tagline.clips":"Crea telecomandi incollando codici IR conosciuti.","panel.tagline.plucker":"Estrai codici IR dai tuoi trasmettitori esistenti.","panel.tagline.mirror":"Osserva in diretta le trasmissioni a infrarossi di Home Assistant.","common.confirm":"Conferma","common.cancel":"Annulla","common.are_you_sure":"Sei sicuro?","common.remove":"Rimuovi","alias.placeholder":"Alias per questo segnale","alias.tag":"alias","alias.clear":"Cancella alias","alias.edit":"Clicca per modificare l'alias","alias.name":"Clicca per dare un nome a questo segnale","picker.emitters_label":"Emettitori IR","picker.add_emitter":"+ Aggiungi emettitore...","picker.no_emitters":"Nessun emettitore IR trovato.","picker.all_emitters_selected":"Tutti gli emettitori selezionati.","picker.receivers_label":"Tramite ricevitore/i:","picker.add_receiver":"+ Aggiungi ricevitore...","picker.no_receivers":"Nessun ricevitore IR trovato.","picker.all_receivers_selected":"Tutti i ricevitori selezionati.","device_type.media_player":"Lettore multimediale","device_type.ac":"Condizionatore","device_type.fan":"Ventilatore","device_type.light":"Luce","device_type.switch":"Interruttore","device_type.screen":"Schermo / Tenda","device_type.other":"Altro","common.name":"Nome","common.device_type":"Tipo di dispositivo","common.name_required":"Il nome è obbligatorio.","common.creating":"Creazione...","common.device_name_placeholder":"es. TV del soggiorno","promote.heading":"Promuovi a dispositivo","promote.device_name":"Nome del dispositivo","promote.device_name_required":"Il nome del dispositivo è obbligatorio.","promote.emitter_required":"Seleziona almeno un emettitore IR.","promote.create_device":"Crea dispositivo","adddev.heading":"Aggiungi dispositivo","adddev.emitter_required":"Scegli almeno un emettitore IR.","adddev.create":"Crea","dup.heading":"Duplica dispositivo","dup.hint_duplicating":"Duplicazione di {name}.","dup.hint_body":"Il nuovo dispositivo riceve una copia di ogni comando, mappatura di azione e assegnazione di emettitore. Potrai cambiare tutto in seguito.","dup.duplicating":"Duplicazione...","dup.duplicate":"Duplica","promote.description":"Crea un nuovo dispositivo HAIR. Potrai poi assegnargli i segnali catturati come comandi.","capture.listening":"In ascolto di un segnale IR…","capture.instruction":'Punta il telecomando verso il ricevitore IR e premi il tasto "{name}".',"capture.remaining":"{seconds}s rimanenti","capture.captured":"Segnale catturato!","capture.protocol":"Protocollo: {protocol}","capture.protocol_raw":"Grezzo","capture.verify":"Ha funzionato? Premi Prova per verificare.","capture.test":"▶ Prova","capture.recapture":"↻ Ricattura","capture.save_next":"Salva e impara il prossimo ▶▶","capture.no_signal":"⚠ Nessun segnale rilevato","capture.tip_point":"Punta il telecomando direttamente verso il ricevitore IR","capture.tip_closer":"Avvicinati (entro 1 metro)","capture.tip_hold":"Tieni premuto brevemente il tasto","capture.try_again":"↻ Riprova","capture.duplicate":"⚠ Segnale duplicato rilevato","capture.duplicate_instruction":'Questo segnale corrisponde al tuo comando "{name}". Alcuni telecomandi usano lo stesso segnale per più tasti.',"capture.recapture_different":"Ricattura un altro","capture.save_anyway":"Salva comunque","capture.error":"⚠ Errore di cattura","capture.learning":'Apprendimento: "{name}"',"test_emitter.heading":"Invia da","test_emitter.sending":"Invio...","test_emitter.send":"Invia","createremote.heading":"Crea telecomando","createremote.type":"Tipo","createremote.blank":"Telecomando vuoto","createremote.from_library":"Dalla libreria di codici","createremote.model":"Modello","createremote.select_model":"Seleziona un modello","popover.assigned_to":"Assegnato a","popover.new_assignment":"+ nuova assegnazione","popover.open_in_devices":"Apri {name} in Dispositivi","popover.triggers":"Trigger","popover.new_trigger":"+ nuovo trigger","popover.any_receiver":"Qualsiasi ricevitore","popover.n_more":"{name} + altri {count}","cmdrow.rename":"Clicca per rinominare","cmdrow.tx_raw_on":"Riproduce il Pronto catturato. Clicca per trasmettere invece i tempi di pacchetto decodificati e puliti.","cmdrow.tx_raw_off":"Trasmette i tempi di pacchetto decodificati e puliti. Clicca per riprodurre invece il Pronto catturato.","cmdrow.sends_times":"Invia questo comando {count} volte","cmdrow.dittos":"Aggiunge {count} ditto NEC","cmdrow.raw_timings":"GREZZO: {count} tempi","cmdrow.not_learned":"Non ancora appreso","cmdrow.edit_code":"Visualizza o modifica il codice","cmdrow.map_action":"Assegna mappatura di azione","cmdrow.actions":"AZIONI","cmdrow.test":"Prova","cmdrow.trigger":"Trigger","cmdrow.edit_trigger":"Modifica trigger","cmdrow.create_trigger":"Crea trigger","cmdrow.delete":"Elimina","cmdrow.learn":"Impara","trigger.alias_tag":"alias","trigger.event":"Evento trigger","trigger.edit_heading":"Modifica trigger","trigger.create_heading":"Crea trigger","trigger.mirror_hint":"Si attiva quando questo segnale arriva dall'esterno di Home Assistant (un telecomando fisico o un'altra app), mai con gli invii della casa stessa.","trigger.name_label":"Nome del trigger","trigger.name_placeholder":"es. Accensione TV","trigger.min_hits":"Pressioni min","trigger.min_hits_hint":"Numero di pressioni in 5s per attivarsi","trigger.scope_hint":"Si attiva una volta per pressione, indipendentemente da quanti ricevitori nell'ambito osservano il segnale.","trigger.save_failed":"Salvataggio non riuscito","common.saving":"Salvataggio...","common.update":"Aggiorna","common.create":"Crea","common.delete":"Elimina","assign.heading":"Assegna segnale","assign.hits":"{count} ricezioni","assign.mode_existing":"Dispositivo esistente","assign.mode_new":"Nuovo dispositivo","assign.send_times":"Numero di invii","assign.send_times_hint":"Trasmette questo comando questo numero di volte per pressione, per i dispositivi che richiedono una ripetizione. Predefinito 1.","assign.ditto_count":"Numero di ditto","assign.ditto_title":"Aggiunge frame di ripetizione dopo il frame principale; alcuni ricevitori rigorosi ne richiedono almeno uno per registrare il comando.","assign.ditto_hint":"Aggiunge frame di ripetizione dopo il frame principale; alcuni ricevitori rigorosi ne richiedono almeno uno per registrare il comando.","assign.assigning":"Assegnazione...","assign.create_assign":"Crea e assegna","assign.assign":"Assegna","assign.target_device":"Dispositivo di destinazione","assign.no_devices":'Nessun dispositivo ancora. Passa a "Nuovo dispositivo" per crearne uno.',"assign.select_device":"Seleziona un dispositivo...","assign.command_name":"Nome del comando","assign.command_placeholder":"Inserisci il nome del comando","assign.select_command":"Seleziona un comando...","assign.custom":"Personalizzato...","assign.command_required":"Il nome del comando è obbligatorio.","assign.target_required":"Seleziona un dispositivo di destinazione.","assign.failed_duplicate":"Assegnazione non riuscita. Il segnale potrebbe avere un codice duplicato sul dispositivo di destinazione.","pluckdlg.blaster_required":"Scegli un trasmettitore da cui estrarre.","pluckdlg.appliance_required":"L'apparecchio è obbligatorio.","pluckdlg.add_heading":"Aggiungi trasmettitore","pluckdlg.loading_blasters":"Caricamento trasmettitori...","pluckdlg.pluck_from":"Estrai da","pluckdlg.select_blaster":"Seleziona un trasmettitore","pluckdlg.appliance":"Apparecchio","pluckdlg.appliance_placeholder":"es. candele","pluckdlg.name_placeholder":"es. Candele del soggiorno","pluckdlg.signal_heading":"Estrai segnale","pluckdlg.pluck_failed":"Estrazione non riuscita.","pluckdlg.no_response":"Nessuna risposta dal trasmettitore. Riprova.","pluckdlg.recognized_as":"Riconosciuto come {protocol}","pluckdlg.valid_pronto":"Codice Pronto valido","pluckdlg.command_help":"Il nome che hai dato a questo codice quando lo hai appreso nell'app del produttore.","pluckdlg.command_placeholder":"es. pwr_on","pluckdlg.plucking":"Estrazione...","pluckdlg.pluck":"Estrai","pluckdlg.captured":"Catturato","pluckdlg.remove_capture":"Rimuovi questa cattura","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Nessun trasmettitore compatibile trovato. Installa un'integrazione IR supportata (come Tuya Local) e apprendi prima un codice.","editor.ditto_disabled_cmd":"Il numero di ditto vale quando il comando è trasmesso come NEC. Sposta la pillola su NEC per attivarlo.","editor.ditto_disabled":"Il numero di ditto vale per i segnali decodificati (oggi NEC). I codici Pronto grezzi vengono trasmessi come catturati.","editor.copied":"Copiato","editor.press_copy":"Premi Cmd/Ctrl+C","editor.valid":"Codice Pronto valido","editor.not_valid":"Non ancora valido","editor.burst_pair.one":"{count} coppia di impulsi","editor.burst_pair.other":"{count} coppie di impulsi","editor.recognized_as":"Riconosciuto come {protocol}","editor.snap_notice":"La portante è a {khz} kHz, fuori dagli standard IR. Alcuni ricevitori la rifiutano.","editor.snapping":"Allineamento...","editor.snap_to":"Allinea a {khz} kHz","editor.edit_command":"Modifica comando","editor.edit_signal":"Modifica segnale","editor.create_signal":"Crea segnale","common.save":"Salva","editor.trigger_note_cmd":"Questo comando ha un trigger che si ripunterà automaticamente.","editor.trigger_note_sig":"Questo segnale ha un trigger che si ripunterà automaticamente.","editor.alias_label":"Alias","editor.alias_optional":"Alias (facoltativo)","editor.pronto_code":"Codice Pronto","editor.select_all":"Seleziona tutto (poi Cmd/Ctrl+C)","editor.alias_placeholder":"es. Accensione","editor.send_times_title":"Trasmette l'intero comando questo numero di volte come pressioni indipendenti, per i dispositivi che richiedono una ripetizione.","editor.ditto_title":"Aggiunge frame di ripetizione dopo il frame principale. Alcuni ricevitori rigorosi, in particolare le apparecchiature audio professionali, ne richiedono almeno uno.","editor.observed.one":"Osservato alla cattura: {count} ditto","editor.observed.other":"Osservato alla cattura: {count} ditto","rel.just_now":"proprio ora","mirror.via":"tramite {name}","mirror.via_n":"tramite {count} emettitori","mirror.not_heard":"non sentito","mirror.heard_in":"sentito l'ultima volta in {areas}","mirror.heard_by":"sentito l'ultima volta da {names}","mirror.chip_automation":"Invio da automazione","mirror.chip_integration":"Invio da integrazione","mirror.chip_test":"Invio di prova manuale","mirror.chip_device":"Dispositivo HAIR","mirror.chip_send":"Invio","mirror.unknown_title":"Segnale IR sconosciuto inviato","mirror.unknown_hint":"{name} ha trasmesso, ma niente era abbastanza vicino da sentire cosa ha detto. Metti un ricevitore a portata d'orecchio per catturare il prossimo invio.","mirror.the_blaster":"Il trasmettitore","mirror.sent":"Inviato!","mirror.sent_all_n":"Inviato! ({sent}/{total})","mirror.sent_partial":"Inviato ({sent}/{total})","mirror.failed":"Non riuscito","mirror.error":"Errore","mirror.sending":"Invio...","mirror.test":"Prova","mirror.stat_sends":"INVII","mirror.stat_not_heard":"NON SENTITI","mirror.stat_emitters":"EMETTITORI","mirror.stat_signals":"SEGNALI","mirror.last_send_ago":"ultimo invio {rel} fa","mirror.last_send_just":"ultimo invio proprio ora","mirror.no_receivers":"nessun ricevitore","mirror.filter_all":"Tutti ({count})","mirror.filter_not_heard":"Non sentiti ({count})","mirror.search":"Cerca invii...","mirror.no_match":"Nessun invio corrisponde.","mirror.signals.one":"{count} segnale","mirror.signals.other":"{count} segnali","mirror.sends_times":"Invia questo segnale {count} volte","mirror.assign_disabled":"Identità sconosciuta -- non è stato sentito nulla di ritorno da assegnare","mirror.assigned_one":"Assegnato a {device} / {command}","mirror.assigned_n":"Assegnato a {count} comandi:","mirror.assign_title":"Assegna questo segnale a un dispositivo HAIR","mirror.test_title":"Invia questo segnale tramite un emettitore per provarlo","mirror.test_disabled":"Identità sconosciuta -- niente da inviare","mirror.trigger_disabled":"Identità sconosciuta -- niente da collegare","mirror.trigger_edit":"Modifica i trigger di questo segnale","mirror.trigger_create":"Si attiva quando questo segnale arriva dall'esterno di Home Assistant","mirror.delete_title":"Cancella questa voce (torna al prossimo invio)","mirror.empty_title":"Ancora nessun invio","mirror.empty_sub":"I comandi inviati dai dispositivi HAIR, dalle automazioni o da qualsiasi integrazione della piattaforma a infrarossi appariranno qui, con la destinazione e chi li ha sentiti.","mirror.del_trigger_title":"Elimina trigger","mirror.del_trigger_msg":"Eliminare definitivamente questo trigger? Le automazioni che lo usano smetteranno di attivarsi.","mirror.clear_title":"Cancella voce del Mirror","mirror.clear_msg":"Rimuovere questa voce dal Mirror? Tornerà al prossimo invio di questo segnale.","common.delete_failed":"Eliminazione non riuscita: {message}","device_type.other_card":"Dispositivo IR","devlist.loading":"Caricamento dispositivi IR...","devlist.empty_title":"Ancora nessun dispositivo IR","devlist.empty_sub":"Aggiungi il tuo primo dispositivo per iniziare.","devlist.add_device_plus":"+ Aggiungi dispositivo","devlist.title":"Dispositivi HAIR","devlist.add_device":"Aggiungi dispositivo","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Nessun TX","devlist.rx_native_title":"Riceve tramite la piattaforma a infrarossi nativa di HA","devlist.rx_bridge_active":"Il vecchio ponte è ancora attivo. Il ricevitore nativo lo sostituisce -- puoi rimuovere il blocco on_pronto: dalla tua configurazione ESPHome.","devlist.rx_bridge_title":"Riceve tramite il vecchio ponte eventi ESPHome","devlist.rx_upgrade_title":"Aggiorna a HA 2026.6+ per il supporto nativo dei ricevitori","devlist.tx_native_title":"Invia tramite la piattaforma a infrarossi nativa di HA","devlist.blasters":"Trasmettitori (estraibili)","devlist.emitters":"Emettitori","devlist.receivers":"Ricevitori","devlist.proxies":"Proxy","devlist.hits_badge":"{count}x ricezioni","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Elimina trigger","devlist.delete_device":"Elimina dispositivo","devlist.open_plucker_title":"Apri nel Plucker","devlist.open_plucker":"Apri nel Plucker","devlist.del_trigger_msg":'Rimuovere "{name}"? Anche l\'entità evento HA associata sarà rimossa.',"devlist.del_device_title":"Elimina dispositivo","devlist.del_device_msg":'Rimuovere "{name}"? Comandi, mappature di azione e assegnazioni di emettitore saranno eliminati. I trigger non sono interessati.',"common.close":"Chiudi","devdetail.name_updated":"Nome aggiornato","devdetail.type_updated":"Tipo di dispositivo aggiornato","devdetail.emitters_updated":"Emettitori aggiornati","devdetail.update_failed":"Aggiornamento non riuscito: {message}","devdetail.reorder_failed":"Riordino non riuscito: {message}","devdetail.mapped_to":"Mappato su {action}","devdetail.mapping_cleared":"Mappatura cancellata","devdetail.mapping_failed":"Mappatura non riuscita: {message}","devdetail.sent_cmd":'"{name}" inviato',"devdetail.send_failed":"Invio non riuscito: {message}","devdetail.cmd_updated":"Comando aggiornato","devdetail.cmd_updated_repointed":"Comando aggiornato. Trigger {names} ripuntato.","devdetail.rename_failed":"Rinomina non riuscita: {message}","devdetail.removed":'"{name}" rimosso',"devdetail.saved":'"{name}" salvato',"devdetail.type":"Tipo","devdetail.commands":"Comandi ({count})","devdetail.no_commands":"Ancora nessun comando. Aggiungine uno qui sotto.","devdetail.drag":"Trascina per riordinare","devdetail.map_action":"Mappa azione","devdetail.none_clear":"Nessuna (cancella)","devdetail.sniff_title":"Cattura un nuovo segnale nello Sniffer","devdetail.sniffed":"+ Segnale annusato","devdetail.clip_title":"Incolla un nuovo segnale in Clips","devdetail.clipped":"+ Segnale incollato","devdetail.mirror_title":"Origlia un invio nel Mirror","devdetail.mirrored":"+ Segnale dal Mirror","devdetail.del_device_title":"Eliminare {name}?","devdetail.del_device_msg":"Questo rimuove tutti i comandi catturati e l'entità creata automaticamente. L'azione non può essere annullata.","devdetail.del_cmd_title":"Eliminare il comando?","devdetail.del_cmd_msg":'Rimuovere "{name}"? Non può essere annullato.',"devdetail.del_trigger_msg":"Rimuovere questo trigger? Anche l'entità evento HA associata sarà rimossa.","rel.min_ago":"{count} min fa","rel.h_ago":"{count}h fa","rel.d_ago":"{count}g fa","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} telecomando","sniffer.remotes.other":"{count} telecomandi","sniffer.scanning":"Ricerca di segnali...","sniffer.empty_title":"Nessun segnale sconosciuto rilevato","sniffer.empty_body":"Quando i tuoi dispositivi ESPHome ricevono segnali IR non riconosciuti, appaiono qui automaticamente.","sniffer.empty_hint":"Prova a premere un tasto di un telecomando non ancora configurato.","sniffer.norx_title":"Nessun ricevitore IR configurato","sniffer.norx_body":"HAIR non ha ancora modo di ricevere segnali IR, quindi lo Sniffer non può catturare nulla.","sniffer.norx_hint":"Configura un ricevitore ESPHome con la piattaforma a infrarossi, oppure controlla in Impostazioni, poi Dispositivi e servizi, che il tuo dispositivo IR sia stato adottato.","sniffer.show_dismissed_title":"Ripristina i telecomandi nascosti in precedenza","sniffer.show_dismissed":"Mostra scartati","sniffer.hide_dismissed":"Nascondi scartati","sniffer.clear_all_title":"Svuota l'intero catalogo degli sconosciuti E la lista degli scartati. Usa Mostra scartati prima di Cancella tutto se vuoi conservare singole voci scartate.","sniffer.clear_all":"Cancella tutto","sniffer.del_signal_title":"Elimina segnale","sniffer.del_signal_msg":"Eliminare definitivamente questo segnale? Non può essere annullato.","sniffer.clear_all_confirm_title":"Cancella tutti i segnali","sniffer.clear_all_confirm_msg":"Rimuovere tutti i segnali e i dispositivi sconosciuti? Non può essere annullato.","sniffer.hair_device":"Dispositivo HAIR","sniffer.promote":"Promuovi","sniffer.dismissed":"scartato","sniffer.restore":"Ripristina","sniffer.dismiss":"Scarta","sniffer.addr":"ind: {address}","sniffer.signals_head":"Segnali ({count})","sniffer.first_seen":"Visto la prima volta: {time}","sniffer.restore_first":"Ripristina prima questo telecomando","sniffer.trigger_create":"Crea un'entità evento HA che si attiva con questo segnale","common.raw":"GREZZO","sniffer.hit_word.one":"ricezione","sniffer.hit_word.other":"ricezioni","sniffer.signal_word.one":"segnale","sniffer.signal_word.other":"segnali","common.loading_plain":"Caricamento...","clips.title":"HAIR Clipper","clips.add_remote":"+ Aggiungi telecomando","clips.empty_title":"Ancora nessun telecomando virtuale","clips.empty_body":"Clipper ti permette di creare telecomandi incollando codici Pronto. Crea un telecomando, poi aggiungi un segnale per ogni tasto.","clips.empty_hint":'Clicca su "+ Aggiungi telecomando" qui sopra per iniziare un telecomando incollato.',"clips.clear_all_title":"Elimina tutti i telecomandi incollati e i loro segnali. I segnali annusati non vengono toccati.","clips.remote_fallback":"Telecomando","clips.add_signal_title":"Aggiungi un segnale a questo telecomando","clips.add_signal":"+ Aggiungi segnale","clips.no_signals":'Ancora nessun segnale. Clicca su "+ Aggiungi segnale" per incollare un codice Pronto.',"clips.delete_remote_title":"Elimina questo telecomando e tutti i suoi segnali","clips.delete_remote":"Elimina telecomando","clips.test_title":"Invia questo segnale tramite un emettitore","clips.clear_all_confirm_title":"Cancella tutti i clip","clips.clear_all_confirm_msg":"Rimuovere tutti i telecomandi incollati e i loro segnali? Non può essere annullato. I segnali annusati non sono interessati.","clips.del_remote_confirm_title":"Elimina telecomando","clips.del_remote_msg_n.one":'Rimuovere "{name}" e il suo {count} segnale? Non può essere annullato.',"clips.del_remote_msg_n.other":'Rimuovere "{name}" e i suoi {count} segnali? Non può essere annullato.',"clips.del_remote_msg":'Rimuovere "{name}"? Non può essere annullato.',"pluck.vendor_unavailable":"L'integrazione di questo trasmettitore non è al momento disponibile. Verifica che l'integrazione del produttore sia caricata.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Aggiungi trasmettitore","pluck.empty_title":"Ancora nessun trasmettitore estratto","pluck.empty_body":"Il Plucker importa i codici IR dai tuoi trasmettitori esistenti per usarli in HAIR senza riapprendere ciascuno.","pluck.empty_hint":'Clicca su "+ Aggiungi trasmettitore" qui sopra per rispecchiare un trasmettitore.',"pluck.clear_all_title":"Elimina tutti i trasmettitori estratti e i loro segnali. I segnali annusati e incollati non vengono toccati.","pluck.blaster_fallback":"Trasmettitore","pluck.promote_title":"Crea un dispositivo HAIR da questo trasmettitore","pluck.pluck_signal_title":"Estrai un codice da questo trasmettitore","pluck.pluck_signal":"+ Estrai segnale","pluck.no_signals":'Ancora nessun segnale. Clicca su "+ Estrai segnale" per prelevare un codice da questo trasmettitore.',"pluck.delete_blaster_title":"Elimina questo trasmettitore e tutti i suoi segnali","pluck.delete_blaster":"Elimina trasmettitore","pluck.clear_all_confirm_title":"Cancella tutti gli estratti","pluck.clear_all_confirm_msg":"Rimuovere tutti i trasmettitori estratti e i loro segnali? Non può essere annullato. I segnali annusati e incollati non sono interessati.","pluck.del_blaster_confirm_title":"Elimina trasmettitore","devdetail.custom_action":"Personalizzato...","devdetail.custom_action_placeholder":"es. temp_30","devdetail.set":"Imposta","vocab.back_return":"Indietro","vocab.brightness_down":"Luminosità -","vocab.brightness_up":"Luminosità +","vocab.channel_down":"Canale -","vocab.channel_up":"Canale +","vocab.close":"Chiudi","vocab.color_temp_cooler":"Bianco più freddo","vocab.color_temp_warmer":"Bianco più caldo","vocab.down":"Giù","vocab.fan_auto":"Ventola: Auto","vocab.fan_high":"Ventola: Alta","vocab.fan_low":"Ventola: Bassa","vocab.fan_medium":"Ventola: Media","vocab.fast_forward":"Avanti veloce","vocab.guide":"Guida","vocab.left":"Sinistra","vocab.menu":"Menu","vocab.mode_auto":"Modalità: Auto","vocab.mode_cool":"Modalità: Raffreddamento","vocab.mode_dry":"Modalità: Deumidificazione","vocab.mode_fan":"Modalità: Ventilazione","vocab.mode_heat":"Modalità: Riscaldamento","vocab.mute":"Muto","vocab.off":"Spento","vocab.on":"Acceso","vocab.open":"Apri","vocab.oscillate":"Oscillazione","vocab.pause":"Pausa","vocab.play":"Riproduci","vocab.power":"Alimentazione","vocab.power_off":"Spegni","vocab.power_on":"Accendi","vocab.power_toggle":"Accendi/Spegni","vocab.rewind":"Riavvolgi","vocab.right":"Destra","vocab.select_ok":"Seleziona/OK","vocab.source_input":"Sorgente/Ingresso","vocab.speed_down":"Velocità -","vocab.speed_up":"Velocità +","vocab.stop":"Stop","vocab.swing_toggle":"Oscillazione alette","vocab.timer":"Timer","vocab.up":"Su","vocab.volume_down":"Volume -","vocab.volume_up":"Volume +"},ja:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"読み込み中…","panel.load_failed":"デバイスの読み込みに失敗しました：{message}","panel.open_menu":"メニューを開く","panel.tab.devices":"デバイス","panel.tagline.devices":"IRデバイスと、それを動かすハードウェアを管理します。","panel.tagline.sniffer":"空中を飛ぶIRコードをライブでキャプチャします。","panel.tagline.clips":"既知のIRコードを貼り付けてリモコンを作成します。","panel.tagline.plucker":"既存のブラスターからIRコードを引き抜きます。","panel.tagline.mirror":"Home Assistantの赤外線送信をライブで確認します。","common.confirm":"確認","common.cancel":"キャンセル","common.are_you_sure":"よろしいですか？","common.remove":"削除","alias.placeholder":"この信号のエイリアス","alias.tag":"エイリアス","alias.clear":"エイリアスをクリア","alias.edit":"クリックしてエイリアスを編集","alias.name":"クリックしてこの信号に名前を付ける","picker.emitters_label":"IRエミッター","picker.add_emitter":"+ エミッターを追加...","picker.no_emitters":"IRエミッターが見つかりません。","picker.all_emitters_selected":"すべてのエミッターが選択されています。","picker.receivers_label":"経由レシーバー：","picker.add_receiver":"+ レシーバーを追加...","picker.no_receivers":"IRレシーバーが見つかりません。","picker.all_receivers_selected":"すべてのレシーバーが選択されています。","device_type.media_player":"メディアプレーヤー","device_type.ac":"エアコン","device_type.fan":"扇風機","device_type.light":"照明","device_type.switch":"スイッチ","device_type.screen":"スクリーン／シェード","device_type.other":"その他","common.name":"名前","common.device_type":"デバイスタイプ","common.name_required":"名前は必須です。","common.creating":"作成中...","common.device_name_placeholder":"例：リビングのテレビ","promote.heading":"デバイスに昇格","promote.device_name":"デバイス名","promote.device_name_required":"デバイス名は必須です。","promote.emitter_required":"IRエミッターを1つ以上選択してください。","promote.create_device":"デバイスを作成","adddev.heading":"デバイスを追加","adddev.emitter_required":"IRエミッターを1つ以上選んでください。","adddev.create":"作成","dup.heading":"デバイスを複製","dup.hint_duplicating":"{name} を複製しています。","dup.hint_body":"新しいデバイスには、すべてのコマンド、アクションマッピング、エミッター割り当てのコピーが引き継がれます。あとから何でも変更できます。","dup.duplicating":"複製中...","dup.duplicate":"複製","promote.description":"新しいHAIRデバイスを作成します。その後、キャプチャした信号をコマンドとして割り当てられます。","capture.listening":"IR信号を待機中…","capture.instruction":"リモコンをIRレシーバーに向けて「{name}」ボタンを押してください。","capture.remaining":"残り{seconds}秒","capture.captured":"信号をキャプチャしました！","capture.protocol":"プロトコル：{protocol}","capture.protocol_raw":"Raw","capture.verify":"動作しましたか？テストを押して確認してください。","capture.test":"▶ テスト","capture.recapture":"↻ 再キャプチャ","capture.save_next":"保存して次を学習 ▶▶","capture.no_signal":"⚠ 信号が検出されません","capture.tip_point":"リモコンをIRレシーバーに直接向けてください","capture.tip_closer":"近づいてください（1メートル以内）","capture.tip_hold":"ボタンを短く押し続けてください","capture.try_again":"↻ もう一度","capture.duplicate":"⚠ 重複した信号を検出","capture.duplicate_instruction":"この信号は「{name}」コマンドと一致します。複数のボタンで同じ信号を使うリモコンもあります。","capture.recapture_different":"別の信号を再キャプチャ","capture.save_anyway":"そのまま保存","capture.error":"⚠ キャプチャエラー","capture.learning":"学習中：「{name}」","test_emitter.heading":"送信元","test_emitter.sending":"送信中...","test_emitter.send":"送信","createremote.heading":"リモコンを作成","createremote.type":"種類","createremote.blank":"空のリモコン","createremote.from_library":"コードライブラリから","createremote.model":"モデル","createremote.select_model":"モデルを選択","popover.assigned_to":"割り当て先","popover.new_assignment":"+ 新しい割り当て","popover.open_in_devices":"{name} をデバイスタブで開く","popover.triggers":"トリガー","popover.new_trigger":"+ 新しいトリガー","popover.any_receiver":"任意のレシーバー","popover.n_more":"{name} + 他{count}件","cmdrow.rename":"クリックして名前を変更","cmdrow.tx_raw_on":"キャプチャしたProntoを再生します。クリックすると、デコード済みのクリーンなパケットタイミングを送信します。","cmdrow.tx_raw_off":"デコード済みのクリーンなパケットタイミングを送信します。クリックすると、キャプチャしたProntoを再生します。","cmdrow.sends_times":"このコマンドを{count}回送信します","cmdrow.dittos":"NECディットーを{count}個追加します","cmdrow.raw_timings":"RAW：{count}タイミング","cmdrow.not_learned":"未学習","cmdrow.edit_code":"コードを表示・編集","cmdrow.map_action":"アクションマッピングを割り当て","cmdrow.actions":"ACTIONS","cmdrow.test":"テスト","cmdrow.trigger":"トリガー","cmdrow.edit_trigger":"トリガーを編集","cmdrow.create_trigger":"トリガーを作成","cmdrow.delete":"削除","cmdrow.learn":"学習","trigger.alias_tag":"エイリアス","trigger.event":"トリガーイベント","trigger.edit_heading":"トリガーを編集","trigger.create_heading":"トリガーを作成","trigger.mirror_hint":"この信号がHome Assistantの外部（物理リモコンや他のアプリ）から届いたときに発火します。家自身の送信では発火しません。","trigger.name_label":"トリガー名","trigger.name_placeholder":"例：テレビ電源","trigger.min_hits":"最小ヒット数","trigger.min_hits_hint":"発火に必要な5秒以内の押下回数","trigger.scope_hint":"対象のレシーバーがいくつ信号を観測しても、1回の押下につき1回だけ発火します。","trigger.save_failed":"保存に失敗しました","common.saving":"保存中...","common.update":"更新","common.create":"作成","common.delete":"削除","assign.heading":"信号を割り当て","assign.hits":"{count}ヒット","assign.mode_existing":"既存のデバイス","assign.mode_new":"新しいデバイス","assign.send_times":"送信回数","assign.send_times_hint":"リピートが必要なデバイス向けに、1回の押下でこのコマンドをこの回数送信します。デフォルトは1。","assign.ditto_count":"ディットー数","assign.ditto_title":"メインフレームの後にリピートフレームを追加します。厳格なレシーバーでは、コマンドを認識させるのに1つ以上必要な場合があります。","assign.ditto_hint":"メインフレームの後にリピートフレームを追加します。厳格なレシーバーでは、コマンドを認識させるのに1つ以上必要な場合があります。","assign.assigning":"割り当て中...","assign.create_assign":"作成して割り当て","assign.assign":"割り当て","assign.target_device":"対象デバイス","assign.no_devices":"デバイスがまだありません。「新しいデバイス」に切り替えて作成してください。","assign.select_device":"デバイスを選択...","assign.command_name":"コマンド名","assign.command_placeholder":"コマンド名を入力","assign.select_command":"コマンドを選択...","assign.custom":"カスタム...","assign.command_required":"コマンド名は必須です。","assign.target_required":"対象デバイスを選択してください。","assign.failed_duplicate":"割り当てに失敗しました。対象デバイスに重複するコードがある可能性があります。","pluckdlg.blaster_required":"引き抜き元のブラスターを選んでください。","pluckdlg.appliance_required":"対象機器は必須です。","pluckdlg.add_heading":"ブラスターを追加","pluckdlg.loading_blasters":"ブラスターを読み込み中...","pluckdlg.pluck_from":"引き抜き元","pluckdlg.select_blaster":"ブラスターを選択","pluckdlg.appliance":"対象機器","pluckdlg.appliance_placeholder":"例：キャンドル","pluckdlg.name_placeholder":"例：リビングのキャンドル","pluckdlg.signal_heading":"信号を引き抜く","pluckdlg.pluck_failed":"引き抜きに失敗しました。","pluckdlg.no_response":"ブラスターから応答がありません。もう一度お試しください。","pluckdlg.recognized_as":"{protocol} として認識","pluckdlg.valid_pronto":"有効なProntoコード","pluckdlg.command_help":"ベンダーアプリでこのコードを学習したときに付けた名前です。","pluckdlg.command_placeholder":"例：pwr_on","pluckdlg.plucking":"引き抜き中...","pluckdlg.pluck":"引き抜く","pluckdlg.captured":"キャプチャ済み","pluckdlg.remove_capture":"このキャプチャを削除","pluckdlg.alias":"エイリアス","pluckdlg.no_blasters":"互換性のあるブラスターが見つかりません。対応するIR統合（Tuya Localなど）をインストールし、先にコードを学習してください。","editor.ditto_disabled_cmd":"ディットー数は、コマンドがNECとして送信されるときに適用されます。ピルをNECに切り替えると有効になります。","editor.ditto_disabled":"ディットー数はデコード済み信号（現在はNEC）に適用されます。RawのProntoコードはキャプチャどおりに送信されます。","editor.copied":"コピーしました","editor.press_copy":"Cmd/Ctrl+Cを押してください","editor.valid":"有効なProntoコード","editor.not_valid":"まだ有効ではありません","editor.burst_pair.one":"{count}バーストペア","editor.burst_pair.other":"{count}バーストペア","editor.recognized_as":"{protocol} として認識","editor.snap_notice":"キャリアは{khz} kHzで、IR標準から外れています。拒否するレシーバーもあります。","editor.snapping":"スナップ中...","editor.snap_to":"{khz} kHzにスナップ","editor.edit_command":"コマンドを編集","editor.edit_signal":"信号を編集","editor.create_signal":"信号を作成","common.save":"保存","editor.trigger_note_cmd":"このコマンドにはトリガーがあり、自動的に再ポイントされます。","editor.trigger_note_sig":"この信号にはトリガーがあり、自動的に再ポイントされます。","editor.alias_label":"エイリアス","editor.alias_optional":"エイリアス（任意）","editor.pronto_code":"Prontoコード","editor.select_all":"すべて選択（その後Cmd/Ctrl+C）","editor.alias_placeholder":"例：電源","editor.send_times_title":"リピートが必要なデバイス向けに、コマンド全体を独立した押下としてこの回数送信します。","editor.ditto_title":"メインフレームの後にリピートフレームを追加します。業務用オーディオ機器など厳格なレシーバーでは、1つ以上必要な場合があります。","editor.observed.one":"キャプチャ時の観測：ディットー{count}個","editor.observed.other":"キャプチャ時の観測：ディットー{count}個","rel.just_now":"たった今","mirror.via":"{name} 経由","mirror.via_n":"{count}台のエミッター経由","mirror.not_heard":"未受信","mirror.heard_in":"最後に {areas} で受信","mirror.heard_by":"最後に {names} が受信","mirror.chip_automation":"オートメーション送信","mirror.chip_integration":"統合からの送信","mirror.chip_test":"手動テスト送信","mirror.chip_device":"HAIRデバイス","mirror.chip_send":"送信","mirror.unknown_title":"不明なIR信号を送信","mirror.unknown_hint":"{name} が発信しましたが、内容を聞き取れる距離に何もいませんでした。次の送信を捉えるには、レシーバーを聞こえる範囲に置いてください。","mirror.the_blaster":"ブラスター","mirror.sent":"送信しました！","mirror.sent_all_n":"送信しました！（{sent}/{total}）","mirror.sent_partial":"送信（{sent}/{total}）","mirror.failed":"失敗","mirror.error":"エラー","mirror.sending":"送信中...","mirror.test":"テスト","mirror.stat_sends":"送信","mirror.stat_not_heard":"未受信","mirror.stat_emitters":"エミッター","mirror.stat_signals":"信号","mirror.last_send_ago":"最終送信 {rel}前","mirror.last_send_just":"最終送信 たった今","mirror.no_receivers":"レシーバーなし","mirror.filter_all":"すべて（{count}）","mirror.filter_not_heard":"未受信（{count}）","mirror.search":"送信を検索...","mirror.no_match":"一致する送信がありません。","mirror.signals.one":"{count}件の信号","mirror.signals.other":"{count}件の信号","mirror.sends_times":"この信号を{count}回送信します","mirror.assign_disabled":"識別情報不明 -- 割り当てられる受信内容がありません","mirror.assigned_one":"{device} / {command} に割り当て済み","mirror.assigned_n":"{count}件のコマンドに割り当て済み：","mirror.assign_title":"この信号をHAIRデバイスに割り当てる","mirror.test_title":"この信号をエミッターから送信してテストする","mirror.test_disabled":"識別情報不明 -- 送信するものがありません","mirror.trigger_disabled":"識別情報不明 -- バインドするものがありません","mirror.trigger_edit":"この信号のトリガーを編集","mirror.trigger_create":"この信号がHome Assistantの外部から届いたときに発火します","mirror.delete_title":"このエントリをクリア（次回送信時に戻ります）","mirror.empty_title":"まだ何も送信されていません","mirror.empty_sub":"HAIRデバイス、オートメーション、赤外線プラットフォーム上の統合が送信したコマンドが、送信先と受信者の情報とともにここに表示されます。","mirror.del_trigger_title":"トリガーを削除","mirror.del_trigger_msg":"このトリガーを完全に削除しますか？これを使用するオートメーションは発火しなくなります。","mirror.clear_title":"Mirrorのエントリをクリア","mirror.clear_msg":"このエントリをMirrorから削除しますか？この信号が次に送信されると戻ります。","common.delete_failed":"削除に失敗しました：{message}","device_type.other_card":"IRデバイス","devlist.loading":"IRデバイスを読み込み中...","devlist.empty_title":"IRデバイスがまだありません","devlist.empty_sub":"最初のデバイスを追加して始めましょう。","devlist.add_device_plus":"+ デバイスを追加","devlist.title":"HAIRデバイス","devlist.add_device":"デバイスを追加","devlist.cmd_badge":"CMD：{count}","devlist.tx_badge":"TX：{count}","devlist.no_tx":"TXなし","devlist.rx_native_title":"HAのネイティブ赤外線プラットフォーム経由で受信","devlist.rx_bridge_active":"レガシーブリッジがまだ有効です。ネイティブレシーバーが優先されるため、ESPHome設定から on_pronto: ブロックを削除できます。","devlist.rx_bridge_title":"レガシーESPHomeイベントバスブリッジ経由で受信","devlist.rx_upgrade_title":"ネイティブレシーバー対応にはHA 2026.6+へアップグレードしてください","devlist.tx_native_title":"HAのネイティブ赤外線プラットフォーム経由で送信","devlist.blasters":"ブラスター（引き抜き可能）","devlist.emitters":"エミッター","devlist.receivers":"レシーバー","devlist.proxies":"プロキシ","devlist.hits_badge":"{count}回ヒット","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"トリガーを削除","devlist.delete_device":"デバイスを削除","devlist.open_plucker_title":"Pluckerで開く","devlist.open_plucker":"Pluckerで開く","devlist.del_trigger_msg":"「{name}」を削除しますか？関連するHAイベントエンティティも削除されます。","devlist.del_device_title":"デバイスを削除","devlist.del_device_msg":"「{name}」を削除しますか？コマンド、アクションマッピング、エミッター割り当てが削除されます。トリガーは影響を受けません。","common.close":"閉じる","devdetail.name_updated":"名前を更新しました","devdetail.type_updated":"デバイスタイプを更新しました","devdetail.emitters_updated":"エミッターを更新しました","devdetail.update_failed":"更新に失敗しました：{message}","devdetail.reorder_failed":"並べ替えに失敗しました：{message}","devdetail.mapped_to":"{action} にマッピングしました","devdetail.mapping_cleared":"マッピングをクリアしました","devdetail.mapping_failed":"マッピングに失敗しました：{message}","devdetail.sent_cmd":"「{name}」を送信しました","devdetail.send_failed":"送信に失敗しました：{message}","devdetail.cmd_updated":"コマンドを更新しました","devdetail.cmd_updated_repointed":"コマンドを更新しました。トリガー {names} を再ポイントしました。","devdetail.rename_failed":"名前の変更に失敗しました：{message}","devdetail.removed":"「{name}」を削除しました","devdetail.saved":"「{name}」を保存しました","devdetail.type":"タイプ","devdetail.commands":"コマンド（{count}）","devdetail.no_commands":"コマンドがまだありません。下から追加してください。","devdetail.drag":"ドラッグして並べ替え","devdetail.map_action":"アクションをマッピング","devdetail.none_clear":"なし（クリア）","devdetail.sniff_title":"Snifferで新しい信号をキャプチャ","devdetail.sniffed":"+ スニフした信号","devdetail.clip_title":"Clipsで新しい信号を貼り付け","devdetail.clipped":"+ クリップした信号","devdetail.mirror_title":"Mirrorで送信を傍受","devdetail.mirrored":"+ Mirrorの信号","devdetail.del_device_title":"{name} を削除しますか？","devdetail.del_device_msg":"キャプチャしたすべてのコマンドと自動作成されたエンティティが削除されます。この操作は元に戻せません。","devdetail.del_cmd_title":"コマンドを削除しますか？","devdetail.del_cmd_msg":"「{name}」を削除しますか？元に戻せません。","devdetail.del_trigger_msg":"このトリガーを削除しますか？関連するHAイベントエンティティも削除されます。","rel.min_ago":"{count}分前","rel.h_ago":"{count}時間前","rel.d_ago":"{count}日前","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count}台のリモコン","sniffer.remotes.other":"{count}台のリモコン","sniffer.scanning":"信号をスキャン中...","sniffer.empty_title":"不明な信号は検出されていません","sniffer.empty_body":"ESPHomeデバイスが未認識のIR信号を受信すると、ここに自動的に表示されます。","sniffer.empty_hint":"まだ設定していないリモコンのボタンを押してみてください。","sniffer.norx_title":"IRレシーバーが設定されていません","sniffer.norx_body":"HAIRにはまだIR信号を受信する手段がないため、Snifferは何もキャプチャできません。","sniffer.norx_hint":"赤外線プラットフォームでESPHomeレシーバーを設定するか、設定→デバイスとサービスでIRデバイスが登録済みか確認してください。","sniffer.show_dismissed_title":"非表示にしたリモコンを復元","sniffer.show_dismissed":"非表示を表示","sniffer.hide_dismissed":"非表示を隠す","sniffer.clear_all_title":"不明カタログ全体と非表示リストを消去します。個別の非表示エントリを残したい場合は、「すべてクリア」の前に「非表示を表示」を使ってください。","sniffer.clear_all":"すべてクリア","sniffer.del_signal_title":"信号を削除","sniffer.del_signal_msg":"この信号を完全に削除しますか？元に戻せません。","sniffer.clear_all_confirm_title":"すべての信号をクリア","sniffer.clear_all_confirm_msg":"すべての不明な信号とデバイスを削除しますか？元に戻せません。","sniffer.hair_device":"HAIRデバイス","sniffer.promote":"昇格","sniffer.dismissed":"非表示","sniffer.restore":"復元","sniffer.dismiss":"非表示にする","sniffer.addr":"アドレス：{address}","sniffer.signals_head":"信号（{count}）","sniffer.first_seen":"初回受信：{time}","sniffer.restore_first":"先にこのリモコンを復元してください","sniffer.trigger_create":"この信号で発火するHAイベントエンティティを作成","common.raw":"RAW","sniffer.hit_word.one":"ヒット","sniffer.hit_word.other":"ヒット","sniffer.signal_word.one":"信号","sniffer.signal_word.other":"信号","common.loading_plain":"読み込み中...","clips.title":"HAIR Clipper","clips.add_remote":"+ リモコンを追加","clips.empty_title":"仮想リモコンがまだありません","clips.empty_body":"ClipperはProntoコードを貼り付けてリモコンを作れるツールです。リモコンを作成し、ボタンごとに信号を追加してください。","clips.empty_hint":"上の「+ リモコンを追加」をクリックして、クリップリモコンを始めましょう。","clips.clear_all_title":"クリップしたすべてのリモコンと信号を削除します。スニフした信号は影響を受けません。","clips.remote_fallback":"リモコン","clips.add_signal_title":"このリモコンに信号を追加","clips.add_signal":"+ 信号を追加","clips.no_signals":"信号がまだありません。「+ 信号を追加」をクリックしてProntoコードを貼り付けてください。","clips.delete_remote_title":"このリモコンとすべての信号を削除","clips.delete_remote":"リモコンを削除","clips.test_title":"この信号をエミッターから送信","clips.clear_all_confirm_title":"すべてのクリップをクリア","clips.clear_all_confirm_msg":"クリップしたすべてのリモコンと信号を削除しますか？元に戻せません。スニフした信号は影響を受けません。","clips.del_remote_confirm_title":"リモコンを削除","clips.del_remote_msg_n.one":"「{name}」とその{count}件の信号を削除しますか？元に戻せません。","clips.del_remote_msg_n.other":"「{name}」とその{count}件の信号を削除しますか？元に戻せません。","clips.del_remote_msg":"「{name}」を削除しますか？元に戻せません。","pluck.vendor_unavailable":"このブラスターの統合は現在利用できません。ベンダー統合が読み込まれているか確認してください。","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ ブラスターを追加","pluck.empty_title":"引き抜いたブラスターがまだありません","pluck.empty_body":"Pluckerは既存のブラスターからIRコードをインポートし、1つずつ学習し直さずにHAIRで使えるようにします。","pluck.empty_hint":"上の「+ ブラスターを追加」をクリックしてブラスターをミラーしましょう。","pluck.clear_all_title":"引き抜いたすべてのブラスターと信号を削除します。スニフ・クリップした信号は影響を受けません。","pluck.blaster_fallback":"ブラスター","pluck.promote_title":"このブラスターからHAIRデバイスを作成","pluck.pluck_signal_title":"このブラスターからコードを引き抜く","pluck.pluck_signal":"+ 信号を引き抜く","pluck.no_signals":"信号がまだありません。「+ 信号を引き抜く」をクリックしてこのブラスターからコードを取り出してください。","pluck.delete_blaster_title":"このブラスターとすべての信号を削除","pluck.delete_blaster":"ブラスターを削除","pluck.clear_all_confirm_title":"引き抜いたものをすべてクリア","pluck.clear_all_confirm_msg":"引き抜いたすべてのブラスターと信号を削除しますか？元に戻せません。スニフ・クリップした信号は影響を受けません。","pluck.del_blaster_confirm_title":"ブラスターを削除","devdetail.custom_action":"カスタム...","devdetail.custom_action_placeholder":"例：temp_30","devdetail.set":"設定","vocab.back_return":"戻る","vocab.brightness_down":"明るさ－","vocab.brightness_up":"明るさ＋","vocab.channel_down":"チャンネル－","vocab.channel_up":"チャンネル＋","vocab.close":"閉じる","vocab.color_temp_cooler":"色温度を冷たく","vocab.color_temp_warmer":"色温度を暖かく","vocab.down":"下","vocab.fan_auto":"風量：自動","vocab.fan_high":"風量：強","vocab.fan_low":"風量：弱","vocab.fan_medium":"風量：中","vocab.fast_forward":"早送り","vocab.guide":"番組表","vocab.left":"左","vocab.menu":"メニュー","vocab.mode_auto":"モード：自動","vocab.mode_cool":"モード：冷房","vocab.mode_dry":"モード：除湿","vocab.mode_fan":"モード：送風","vocab.mode_heat":"モード：暖房","vocab.mute":"消音","vocab.off":"オフ","vocab.on":"オン","vocab.open":"開く","vocab.oscillate":"首振り","vocab.pause":"一時停止","vocab.play":"再生","vocab.power":"電源","vocab.power_off":"電源オフ","vocab.power_on":"電源オン","vocab.power_toggle":"電源切替","vocab.rewind":"早戻し","vocab.right":"右","vocab.select_ok":"決定","vocab.source_input":"入力切替","vocab.speed_down":"スピード－","vocab.speed_up":"スピード＋","vocab.stop":"停止","vocab.swing_toggle":"スイング切替","vocab.timer":"タイマー","vocab.up":"上","vocab.volume_down":"音量－","vocab.volume_up":"音量＋"},nl:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Laden…","panel.load_failed":"Apparaten laden mislukt: {message}","panel.open_menu":"Menu openen","panel.tab.devices":"Apparaten","panel.tagline.devices":"Beheer je IR-apparaten en de hardware die ze aanstuurt.","panel.tagline.sniffer":"Vang IR-codes live uit de lucht.","panel.tagline.clips":"Bouw afstandsbedieningen door bekende IR-codes te plakken.","panel.tagline.plucker":"Pluk IR-codes uit je bestaande blasters.","panel.tagline.mirror":"Bekijk live de infraroodtransmissies van Home Assistant.","common.confirm":"Bevestigen","common.cancel":"Annuleren","common.are_you_sure":"Weet je het zeker?","common.remove":"Verwijderen","alias.placeholder":"Alias voor dit signaal","alias.tag":"alias","alias.clear":"Alias wissen","alias.edit":"Klik om de alias te bewerken","alias.name":"Klik om dit signaal een naam te geven","picker.emitters_label":"IR-zenders","picker.add_emitter":"+ Zender toevoegen...","picker.no_emitters":"Geen IR-zenders gevonden.","picker.all_emitters_selected":"Alle zenders geselecteerd.","picker.receivers_label":"Via ontvanger(s):","picker.add_receiver":"+ Ontvanger toevoegen...","picker.no_receivers":"Geen IR-ontvangers gevonden.","picker.all_receivers_selected":"Alle ontvangers geselecteerd.","device_type.media_player":"Mediaspeler","device_type.ac":"Airco","device_type.fan":"Ventilator","device_type.light":"Lamp","device_type.switch":"Schakelaar","device_type.screen":"Scherm / Zonwering","device_type.other":"Overig","common.name":"Naam","common.device_type":"Apparaattype","common.name_required":"Naam is verplicht.","common.creating":"Aanmaken...","common.device_name_placeholder":"bijv. Woonkamer-tv","promote.heading":"Promoveren tot apparaat","promote.device_name":"Apparaatnaam","promote.device_name_required":"Apparaatnaam is verplicht.","promote.emitter_required":"Selecteer minstens één IR-zender.","promote.create_device":"Apparaat aanmaken","adddev.heading":"Apparaat toevoegen","adddev.emitter_required":"Kies minstens één IR-zender.","adddev.create":"Aanmaken","dup.heading":"Apparaat dupliceren","dup.hint_duplicating":"{name} wordt gedupliceerd.","dup.hint_body":"Het nieuwe apparaat krijgt een kopie van elk commando, elke actietoewijzing en elke zendertoewijzing. Je kunt daarna alles aanpassen.","dup.duplicating":"Dupliceren...","dup.duplicate":"Dupliceren","promote.description":"Maak een nieuw HAIR-apparaat aan. Daarna kun je er gevangen signalen als commando's aan toewijzen.","capture.listening":"Wachten op IR-signaal…","capture.instruction":'Richt je afstandsbediening op de IR-ontvanger en druk op de knop "{name}".',"capture.remaining":"{seconds}s resterend","capture.captured":"Signaal gevangen!","capture.protocol":"Protocol: {protocol}","capture.protocol_raw":"Ruw","capture.verify":"Werkte het? Druk op Testen om te controleren.","capture.test":"▶ Testen","capture.recapture":"↻ Opnieuw vangen","capture.save_next":"Opslaan en volgende leren ▶▶","capture.no_signal":"⚠ Geen signaal gedetecteerd","capture.tip_point":"Richt de afstandsbediening rechtstreeks op de IR-ontvanger","capture.tip_closer":"Kom dichterbij (binnen 1 meter)","capture.tip_hold":"Houd de knop kort ingedrukt","capture.try_again":"↻ Opnieuw proberen","capture.duplicate":"⚠ Dubbel signaal gedetecteerd","capture.duplicate_instruction":'Dit signaal komt overeen met je commando "{name}". Sommige afstandsbedieningen gebruiken hetzelfde signaal voor meerdere knoppen.',"capture.recapture_different":"Ander signaal vangen","capture.save_anyway":"Toch opslaan","capture.error":"⚠ Vangfout","capture.learning":'Leren: "{name}"',"test_emitter.heading":"Verzenden vanaf","test_emitter.sending":"Verzenden...","test_emitter.send":"Verzenden","createremote.heading":"Afstandsbediening aanmaken","createremote.type":"Type","createremote.blank":"Lege afstandsbediening","createremote.from_library":"Uit de codebibliotheek","createremote.model":"Model","createremote.select_model":"Selecteer een model","popover.assigned_to":"Toegewezen aan","popover.new_assignment":"+ nieuwe toewijzing","popover.open_in_devices":"{name} openen in Apparaten","popover.triggers":"Triggers","popover.new_trigger":"+ nieuwe trigger","popover.any_receiver":"Elke ontvanger","popover.n_more":"{name} + {count} meer","cmdrow.rename":"Klik om te hernoemen","cmdrow.tx_raw_on":"Speelt de gevangen Pronto af. Klik om in plaats daarvan schone gedecodeerde pakkettimings te verzenden.","cmdrow.tx_raw_off":"Verzendt schone gedecodeerde pakkettimings. Klik om in plaats daarvan de gevangen Pronto af te spelen.","cmdrow.sends_times":"Verzendt dit commando {count} keer","cmdrow.dittos":"Voegt {count} NEC-ditto's toe","cmdrow.raw_timings":"RUW: {count} timings","cmdrow.not_learned":"Nog niet geleerd","cmdrow.edit_code":"Code bekijken of bewerken","cmdrow.map_action":"Actietoewijzing instellen","cmdrow.actions":"ACTIES","cmdrow.test":"Testen","cmdrow.trigger":"Trigger","cmdrow.edit_trigger":"Trigger bewerken","cmdrow.create_trigger":"Trigger aanmaken","cmdrow.delete":"Verwijderen","cmdrow.learn":"Leren","trigger.alias_tag":"alias","trigger.event":"Triggergebeurtenis","trigger.edit_heading":"Trigger bewerken","trigger.create_heading":"Trigger aanmaken","trigger.mirror_hint":"Vuurt wanneer dit signaal van buiten Home Assistant komt (een fysieke afstandsbediening of een andere app), nooit bij verzendingen van het huis zelf.","trigger.name_label":"Triggernaam","trigger.name_placeholder":"bijv. TV aan/uit","trigger.min_hits":"Min. drukken","trigger.min_hits_hint":"Aantal drukken binnen 5s om te vuren","trigger.scope_hint":"Vuurt één keer per druk, ongeacht hoeveel ontvangers in het bereik het signaal waarnemen.","trigger.save_failed":"Opslaan mislukt","common.saving":"Opslaan...","common.update":"Bijwerken","common.create":"Aanmaken","common.delete":"Verwijderen","assign.heading":"Signaal toewijzen","assign.hits":"{count} ontvangsten","assign.mode_existing":"Bestaand apparaat","assign.mode_new":"Nieuw apparaat","assign.send_times":"Aantal verzendingen","assign.send_times_hint":"Verzendt dit commando zo vaak per druk, voor apparaten die een herhaling nodig hebben. Standaard 1.","assign.ditto_count":"Aantal ditto's","assign.ditto_title":"Voegt herhalingsframes toe na het hoofdframe; sommige strenge ontvangers vereisen er minstens één om het commando te registreren.","assign.ditto_hint":"Voegt herhalingsframes toe na het hoofdframe; sommige strenge ontvangers vereisen er minstens één om het commando te registreren.","assign.assigning":"Toewijzen...","assign.create_assign":"Aanmaken en toewijzen","assign.assign":"Toewijzen","assign.target_device":"Doelapparaat","assign.no_devices":'Nog geen apparaten. Schakel naar "Nieuw apparaat" om er een aan te maken.',"assign.select_device":"Selecteer een apparaat...","assign.command_name":"Commandonaam","assign.command_placeholder":"Voer de commandonaam in","assign.select_command":"Selecteer een commando...","assign.custom":"Aangepast...","assign.command_required":"Commandonaam is verplicht.","assign.target_required":"Selecteer een doelapparaat.","assign.failed_duplicate":"Toewijzen mislukt. Het signaal heeft mogelijk een dubbele code op het doelapparaat.","pluckdlg.blaster_required":"Kies een blaster om uit te plukken.","pluckdlg.appliance_required":"Apparaat is verplicht.","pluckdlg.add_heading":"Blaster toevoegen","pluckdlg.loading_blasters":"Blasters laden...","pluckdlg.pluck_from":"Plukken uit","pluckdlg.select_blaster":"Selecteer een blaster","pluckdlg.appliance":"Apparaat","pluckdlg.appliance_placeholder":"bijv. kaarsen","pluckdlg.name_placeholder":"bijv. Woonkamerkaarsen","pluckdlg.signal_heading":"Signaal plukken","pluckdlg.pluck_failed":"Plukken mislukt.","pluckdlg.no_response":"Geen reactie van de blaster. Probeer opnieuw.","pluckdlg.recognized_as":"Herkend als {protocol}","pluckdlg.valid_pronto":"Geldige Pronto-code","pluckdlg.command_help":"De naam die je deze code gaf toen je hem leerde in de app van de fabrikant.","pluckdlg.command_placeholder":"bijv. pwr_on","pluckdlg.plucking":"Plukken...","pluckdlg.pluck":"Plukken","pluckdlg.captured":"Gevangen","pluckdlg.remove_capture":"Deze vangst verwijderen","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Geen compatibele blasters gevonden. Installeer een ondersteunde IR-integratie (zoals Tuya Local) en leer eerst een code.","editor.ditto_disabled_cmd":"Het aantal ditto's geldt wanneer het commando als NEC wordt verzonden. Zet de pil op NEC om het in te schakelen.","editor.ditto_disabled":"Het aantal ditto's geldt voor gedecodeerde signalen (nu NEC). Ruwe Pronto-codes worden verzonden zoals gevangen.","editor.copied":"Gekopieerd","editor.press_copy":"Druk op Cmd/Ctrl+C","editor.valid":"Geldige Pronto-code","editor.not_valid":"Nog niet geldig","editor.burst_pair.one":"{count} burstpaar","editor.burst_pair.other":"{count} burstparen","editor.recognized_as":"Herkend als {protocol}","editor.snap_notice":"De draaggolf is {khz} kHz, buiten de IR-standaarden. Sommige ontvangers wijzen hem af.","editor.snapping":"Aanpassen...","editor.snap_to":"Aanpassen naar {khz} kHz","editor.edit_command":"Commando bewerken","editor.edit_signal":"Signaal bewerken","editor.create_signal":"Signaal aanmaken","common.save":"Opslaan","editor.trigger_note_cmd":"Dit commando heeft een trigger die zichzelf automatisch opnieuw richt.","editor.trigger_note_sig":"Dit signaal heeft een trigger die zichzelf automatisch opnieuw richt.","editor.alias_label":"Alias","editor.alias_optional":"Alias (optioneel)","editor.pronto_code":"Pronto-code","editor.select_all":"Alles selecteren (dan Cmd/Ctrl+C)","editor.alias_placeholder":"bijv. Aan/uit","editor.send_times_title":"Verzendt het hele commando zo vaak als onafhankelijke drukken, voor apparaten die een herhaling nodig hebben.","editor.ditto_title":"Voegt herhalingsframes toe na het hoofdframe. Sommige strenge ontvangers, vooral professionele audioapparatuur, vereisen er minstens één.","editor.observed.one":"Waargenomen bij vangst: {count} ditto","editor.observed.other":"Waargenomen bij vangst: {count} ditto's","rel.just_now":"zojuist","mirror.via":"via {name}","mirror.via_n":"via {count} zenders","mirror.not_heard":"niet gehoord","mirror.heard_in":"laatst gehoord in {areas}","mirror.heard_by":"laatst gehoord door {names}","mirror.chip_automation":"Automatiseringsverzending","mirror.chip_integration":"Integratieverzending","mirror.chip_test":"Handmatige testverzending","mirror.chip_device":"HAIR-apparaat","mirror.chip_send":"Verzending","mirror.unknown_title":"Onbekend IR-signaal verzonden","mirror.unknown_hint":"{name} vuurde, maar niets was dichtbij genoeg om te horen wat er gezegd werd. Plaats een ontvanger binnen gehoorsafstand om de volgende verzending op te vangen.","mirror.the_blaster":"De blaster","mirror.sent":"Verzonden!","mirror.sent_all_n":"Verzonden! ({sent}/{total})","mirror.sent_partial":"Verzonden ({sent}/{total})","mirror.failed":"Mislukt","mirror.error":"Fout","mirror.sending":"Verzenden...","mirror.test":"Testen","mirror.stat_sends":"VERZENDINGEN","mirror.stat_not_heard":"NIET GEHOORD","mirror.stat_emitters":"ZENDERS","mirror.stat_signals":"SIGNALEN","mirror.last_send_ago":"laatste verzending {rel} geleden","mirror.last_send_just":"laatste verzending zojuist","mirror.no_receivers":"geen ontvangers","mirror.filter_all":"Alle ({count})","mirror.filter_not_heard":"Niet gehoord ({count})","mirror.search":"Verzendingen zoeken...","mirror.no_match":"Geen verzending komt overeen.","mirror.signals.one":"{count} signaal","mirror.signals.other":"{count} signalen","mirror.sends_times":"Verzendt dit signaal {count} keer","mirror.assign_disabled":"Identiteit onbekend -- niets teruggehoord om toe te wijzen","mirror.assigned_one":"Toegewezen aan {device} / {command}","mirror.assigned_n":"Toegewezen aan {count} commando's:","mirror.assign_title":"Dit signaal toewijzen aan een HAIR-apparaat","mirror.test_title":"Dit signaal via een zender verzenden om het te testen","mirror.test_disabled":"Identiteit onbekend -- niets om te verzenden","mirror.trigger_disabled":"Identiteit onbekend -- niets om te koppelen","mirror.trigger_edit":"Trigger(s) van dit signaal bewerken","mirror.trigger_create":"Vuurt wanneer dit signaal van buiten Home Assistant komt","mirror.delete_title":"Deze regel wissen (komt terug bij de volgende verzending)","mirror.empty_title":"Nog niets verzonden","mirror.empty_sub":"Commando's verzonden door HAIR-apparaten, automatiseringen of elke integratie op het infraroodplatform verschijnen hier, met hun bestemming en wie ze hoorde.","mirror.del_trigger_title":"Trigger verwijderen","mirror.del_trigger_msg":"Deze trigger permanent verwijderen? Automatiseringen die hem gebruiken vuren niet meer.","mirror.clear_title":"Mirror-regel wissen","mirror.clear_msg":"Deze regel uit de Mirror verwijderen? Hij komt terug zodra dit signaal opnieuw wordt verzonden.","common.delete_failed":"Verwijderen mislukt: {message}","device_type.other_card":"IR-apparaat","devlist.loading":"IR-apparaten laden...","devlist.empty_title":"Nog geen IR-apparaten","devlist.empty_sub":"Voeg je eerste apparaat toe om te beginnen.","devlist.add_device_plus":"+ Apparaat toevoegen","devlist.title":"HAIR-apparaten","devlist.add_device":"Apparaat toevoegen","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Geen TX","devlist.rx_native_title":"Ontvangt via het native infraroodplatform van HA","devlist.rx_bridge_active":"De oude brug is nog actief. De native ontvanger vervangt hem -- je kunt het on_pronto:-blok uit je ESPHome-configuratie verwijderen.","devlist.rx_bridge_title":"Ontvangt via de oude ESPHome-gebeurtenisbrug","devlist.rx_upgrade_title":"Upgrade naar HA 2026.6+ voor native ontvangerondersteuning","devlist.tx_native_title":"Verzendt via het native infraroodplatform van HA","devlist.blasters":"Blasters (plukbaar)","devlist.emitters":"Zenders","devlist.receivers":"Ontvangers","devlist.proxies":"Proxy's","devlist.hits_badge":"{count}x ontvangsten","devlist.on":"AAN","devlist.off":"UIT","devlist.delete_trigger":"Trigger verwijderen","devlist.delete_device":"Apparaat verwijderen","devlist.open_plucker_title":"Openen in de Plucker","devlist.open_plucker":"Openen in Plucker","devlist.del_trigger_msg":'"{name}" verwijderen? De bijbehorende HA-gebeurtenisentiteit wordt ook verwijderd.',"devlist.del_device_title":"Apparaat verwijderen","devlist.del_device_msg":'"{name}" verwijderen? Commando\'s, actietoewijzingen en zendertoewijzingen worden verwijderd. Triggers blijven onaangetast.',"common.close":"Sluiten","devdetail.name_updated":"Naam bijgewerkt","devdetail.type_updated":"Apparaattype bijgewerkt","devdetail.emitters_updated":"Zenders bijgewerkt","devdetail.update_failed":"Bijwerken mislukt: {message}","devdetail.reorder_failed":"Herordenen mislukt: {message}","devdetail.mapped_to":"Toegewezen aan {action}","devdetail.mapping_cleared":"Toewijzing gewist","devdetail.mapping_failed":"Toewijzing mislukt: {message}","devdetail.sent_cmd":'"{name}" verzonden',"devdetail.send_failed":"Verzenden mislukt: {message}","devdetail.cmd_updated":"Commando bijgewerkt","devdetail.cmd_updated_repointed":"Commando bijgewerkt. Trigger {names} opnieuw gericht.","devdetail.rename_failed":"Hernoemen mislukt: {message}","devdetail.removed":'"{name}" verwijderd',"devdetail.saved":'"{name}" opgeslagen',"devdetail.type":"Type","devdetail.commands":"Commando's ({count})","devdetail.no_commands":"Nog geen commando's. Voeg er hieronder een toe.","devdetail.drag":"Sleep om te herordenen","devdetail.map_action":"Actie toewijzen","devdetail.none_clear":"Geen (wissen)","devdetail.sniff_title":"Een nieuw signaal vangen in de Sniffer","devdetail.sniffed":"+ Gesnoven signaal","devdetail.clip_title":"Een nieuw signaal plakken in Clips","devdetail.clipped":"+ Geplakt signaal","devdetail.mirror_title":"Een verzending afluisteren in de Mirror","devdetail.mirrored":"+ Signaal uit de Mirror","devdetail.del_device_title":"{name} verwijderen?","devdetail.del_device_msg":"Dit verwijdert alle gevangen commando's en de automatisch aangemaakte entiteit. Dit kan niet ongedaan worden gemaakt.","devdetail.del_cmd_title":"Commando verwijderen?","devdetail.del_cmd_msg":'"{name}" verwijderen? Dit kan niet ongedaan worden gemaakt.',"devdetail.del_trigger_msg":"Deze trigger verwijderen? De bijbehorende HA-gebeurtenisentiteit wordt ook verwijderd.","rel.min_ago":"{count} min geleden","rel.h_ago":"{count}u geleden","rel.d_ago":"{count}d geleden","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} afstandsbediening","sniffer.remotes.other":"{count} afstandsbedieningen","sniffer.scanning":"Zoeken naar signalen...","sniffer.empty_title":"Geen onbekende signalen gedetecteerd","sniffer.empty_body":"Wanneer je ESPHome-apparaten niet-herkende IR-signalen ontvangen, verschijnen ze hier automatisch.","sniffer.empty_hint":"Druk eens op een knop van een afstandsbediening die nog niet is ingesteld.","sniffer.norx_title":"Geen IR-ontvanger ingesteld","sniffer.norx_body":"HAIR kan nog geen IR-signalen ontvangen, dus de Sniffer kan niets vangen.","sniffer.norx_hint":"Stel een ESPHome-ontvanger in met het infraroodplatform, of controleer via Instellingen, dan Apparaten en diensten, of je IR-apparaat is toegevoegd.","sniffer.show_dismissed_title":"Eerder verborgen afstandsbedieningen herstellen","sniffer.show_dismissed":"Verworpen tonen","sniffer.hide_dismissed":"Verworpen verbergen","sniffer.clear_all_title":"Wist de hele catalogus van onbekenden EN de verworpen-lijst. Gebruik Verworpen tonen vóór Alles wissen als je losse verworpen regels wilt behouden.","sniffer.clear_all":"Alles wissen","sniffer.del_signal_title":"Signaal verwijderen","sniffer.del_signal_msg":"Dit signaal permanent verwijderen? Dit kan niet ongedaan worden gemaakt.","sniffer.clear_all_confirm_title":"Alle signalen wissen","sniffer.clear_all_confirm_msg":"Alle onbekende signalen en apparaten verwijderen? Dit kan niet ongedaan worden gemaakt.","sniffer.hair_device":"HAIR-apparaat","sniffer.promote":"Promoveren","sniffer.dismissed":"verworpen","sniffer.restore":"Herstellen","sniffer.dismiss":"Verwerpen","sniffer.addr":"adr: {address}","sniffer.signals_head":"Signalen ({count})","sniffer.first_seen":"Eerst gezien: {time}","sniffer.restore_first":"Herstel eerst deze afstandsbediening","sniffer.trigger_create":"Een HA-gebeurtenisentiteit aanmaken die vuurt bij dit signaal","common.raw":"RUW","sniffer.hit_word.one":"ontvangst","sniffer.hit_word.other":"ontvangsten","sniffer.signal_word.one":"signaal","sniffer.signal_word.other":"signalen","common.loading_plain":"Laden...","clips.title":"HAIR Clipper","clips.add_remote":"+ Afstandsbediening toevoegen","clips.empty_title":"Nog geen virtuele afstandsbedieningen","clips.empty_body":"Met Clipper bouw je afstandsbedieningen door Pronto-codes te plakken. Maak een afstandsbediening aan en voeg dan per knop een signaal toe.","clips.empty_hint":'Klik hierboven op "+ Afstandsbediening toevoegen" om een geplakte afstandsbediening te beginnen.',"clips.clear_all_title":"Verwijdert alle geplakte afstandsbedieningen en hun signalen. Gesnoven signalen blijven onaangetast.","clips.remote_fallback":"Afstandsbediening","clips.add_signal_title":"Een signaal toevoegen aan deze afstandsbediening","clips.add_signal":"+ Signaal toevoegen","clips.no_signals":'Nog geen signalen. Klik op "+ Signaal toevoegen" om een Pronto-code te plakken.',"clips.delete_remote_title":"Deze afstandsbediening en al haar signalen verwijderen","clips.delete_remote":"Afstandsbediening verwijderen","clips.test_title":"Dit signaal via een zender verzenden","clips.clear_all_confirm_title":"Alle clips wissen","clips.clear_all_confirm_msg":"Alle geplakte afstandsbedieningen en hun signalen verwijderen? Dit kan niet ongedaan worden gemaakt. Gesnoven signalen worden niet geraakt.","clips.del_remote_confirm_title":"Afstandsbediening verwijderen","clips.del_remote_msg_n.one":'"{name}" en zijn {count} signaal verwijderen? Dit kan niet ongedaan worden gemaakt.',"clips.del_remote_msg_n.other":'"{name}" en zijn {count} signalen verwijderen? Dit kan niet ongedaan worden gemaakt.',"clips.del_remote_msg":'"{name}" verwijderen? Dit kan niet ongedaan worden gemaakt.',"pluck.vendor_unavailable":"De integratie van deze blaster is momenteel niet beschikbaar. Controleer of de fabrikantintegratie is geladen.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Blaster toevoegen","pluck.empty_title":"Nog geen geplukte blasters","pluck.empty_body":"De Plucker importeert IR-codes uit je bestaande blasters zodat je ze in HAIR kunt gebruiken zonder elk opnieuw te leren.","pluck.empty_hint":'Klik hierboven op "+ Blaster toevoegen" om een blaster te spiegelen.',"pluck.clear_all_title":"Verwijdert alle geplukte blasters en hun signalen. Gesnoven en geplakte signalen blijven onaangetast.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Een HAIR-apparaat aanmaken van deze blaster","pluck.pluck_signal_title":"Een code van deze blaster plukken","pluck.pluck_signal":"+ Signaal plukken","pluck.no_signals":'Nog geen signalen. Klik op "+ Signaal plukken" om een code van deze blaster te halen.',"pluck.delete_blaster_title":"Deze blaster en al zijn signalen verwijderen","pluck.delete_blaster":"Blaster verwijderen","pluck.clear_all_confirm_title":"Alles geplukte wissen","pluck.clear_all_confirm_msg":"Alle geplukte blasters en hun signalen verwijderen? Dit kan niet ongedaan worden gemaakt. Gesnoven en geplakte signalen worden niet geraakt.","pluck.del_blaster_confirm_title":"Blaster verwijderen","devdetail.custom_action":"Aangepast...","devdetail.custom_action_placeholder":"bijv. temp_30","devdetail.set":"Instellen","vocab.back_return":"Terug","vocab.brightness_down":"Helderheid -","vocab.brightness_up":"Helderheid +","vocab.channel_down":"Kanaal -","vocab.channel_up":"Kanaal +","vocab.close":"Sluiten","vocab.color_temp_cooler":"Koeler wit","vocab.color_temp_warmer":"Warmer wit","vocab.down":"Omlaag","vocab.fan_auto":"Ventilator: Auto","vocab.fan_high":"Ventilator: Hoog","vocab.fan_low":"Ventilator: Laag","vocab.fan_medium":"Ventilator: Middel","vocab.fast_forward":"Vooruitspoelen","vocab.guide":"Gids","vocab.left":"Links","vocab.menu":"Menu","vocab.mode_auto":"Modus: Auto","vocab.mode_cool":"Modus: Koelen","vocab.mode_dry":"Modus: Ontvochtigen","vocab.mode_fan":"Modus: Ventileren","vocab.mode_heat":"Modus: Verwarmen","vocab.mute":"Dempen","vocab.off":"Uit","vocab.on":"Aan","vocab.open":"Openen","vocab.oscillate":"Zwenken","vocab.pause":"Pauze","vocab.play":"Afspelen","vocab.power":"Aan/uit","vocab.power_off":"Uitschakelen","vocab.power_on":"Inschakelen","vocab.power_toggle":"Aan/uit wisselen","vocab.rewind":"Terugspoelen","vocab.right":"Rechts","vocab.select_ok":"Selecteren/OK","vocab.source_input":"Bron/Ingang","vocab.speed_down":"Snelheid -","vocab.speed_up":"Snelheid +","vocab.stop":"Stop","vocab.swing_toggle":"Lamellen zwenken","vocab.timer":"Timer","vocab.up":"Omhoog","vocab.volume_down":"Volume -","vocab.volume_up":"Volume +"},pl:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Ładowanie…","panel.load_failed":"Nie udało się załadować urządzeń: {message}","panel.open_menu":"Otwórz menu","panel.tab.devices":"Urządzenia","panel.tagline.devices":"Zarządzaj urządzeniami IR i sprzętem, który nimi steruje.","panel.tagline.sniffer":"Przechwytuj kody IR na żywo z powietrza.","panel.tagline.clips":"Twórz piloty, wklejając znane kody IR.","panel.tagline.plucker":"Wyciągaj kody IR z istniejących nadajników.","panel.tagline.mirror":"Obserwuj na żywo transmisje podczerwieni Home Assistant.","common.confirm":"Potwierdź","common.cancel":"Anuluj","common.are_you_sure":"Czy na pewno?","common.remove":"Usuń","alias.placeholder":"Alias dla tego sygnału","alias.tag":"alias","alias.clear":"Wyczyść alias","alias.edit":"Kliknij, aby edytować alias","alias.name":"Kliknij, aby nazwać ten sygnał","picker.emitters_label":"Nadajniki IR","picker.add_emitter":"+ Dodaj nadajnik...","picker.no_emitters":"Nie znaleziono nadajników IR.","picker.all_emitters_selected":"Wszystkie nadajniki wybrane.","picker.receivers_label":"Przez odbiornik(i):","picker.add_receiver":"+ Dodaj odbiornik...","picker.no_receivers":"Nie znaleziono odbiorników IR.","picker.all_receivers_selected":"Wszystkie odbiorniki wybrane.","device_type.media_player":"Odtwarzacz multimedialny","device_type.ac":"Klimatyzator","device_type.fan":"Wentylator","device_type.light":"Światło","device_type.switch":"Przełącznik","device_type.screen":"Ekran / Roleta","device_type.other":"Inne","common.name":"Nazwa","common.device_type":"Typ urządzenia","common.name_required":"Nazwa jest wymagana.","common.creating":"Tworzenie...","common.device_name_placeholder":"np. Telewizor w salonie","promote.heading":"Awansuj na urządzenie","promote.device_name":"Nazwa urządzenia","promote.device_name_required":"Nazwa urządzenia jest wymagana.","promote.emitter_required":"Wybierz co najmniej jeden nadajnik IR.","promote.create_device":"Utwórz urządzenie","adddev.heading":"Dodaj urządzenie","adddev.emitter_required":"Wybierz co najmniej jeden nadajnik IR.","adddev.create":"Utwórz","dup.heading":"Duplikuj urządzenie","dup.hint_duplicating":"Duplikowanie {name}.","dup.hint_body":"Nowe urządzenie otrzymuje kopię każdego polecenia, mapowania akcji i przypisania nadajnika. Wszystko możesz później zmienić.","dup.duplicating":"Duplikowanie...","dup.duplicate":"Duplikuj","promote.description":"Utwórz nowe urządzenie HAIR. Następnie możesz przypisać mu przechwycone sygnały jako polecenia.","capture.listening":"Nasłuchiwanie sygnału IR…","capture.instruction":'Skieruj pilota na odbiornik IR i naciśnij przycisk "{name}".',"capture.remaining":"Pozostało {seconds}s","capture.captured":"Sygnał przechwycony!","capture.protocol":"Protokół: {protocol}","capture.protocol_raw":"Surowy","capture.verify":"Zadziałało? Naciśnij Test, aby sprawdzić.","capture.test":"▶ Test","capture.recapture":"↻ Przechwyć ponownie","capture.save_next":"Zapisz i ucz następny ▶▶","capture.no_signal":"⚠ Nie wykryto sygnału","capture.tip_point":"Skieruj pilota bezpośrednio na odbiornik IR","capture.tip_closer":"Podejdź bliżej (do 1 metra)","capture.tip_hold":"Krótko przytrzymaj przycisk","capture.try_again":"↻ Spróbuj ponownie","capture.duplicate":"⚠ Wykryto zduplikowany sygnał","capture.duplicate_instruction":'Ten sygnał odpowiada poleceniu "{name}". Niektóre piloty używają tego samego sygnału dla kilku przycisków.',"capture.recapture_different":"Przechwyć inny","capture.save_anyway":"Zapisz mimo to","capture.error":"⚠ Błąd przechwytywania","capture.learning":'Uczenie: "{name}"',"test_emitter.heading":"Wyślij z","test_emitter.sending":"Wysyłanie...","test_emitter.send":"Wyślij","createremote.heading":"Utwórz pilota","createremote.type":"Typ","createremote.blank":"Pusty pilot","createremote.from_library":"Z biblioteki kodów","createremote.model":"Model","createremote.select_model":"Wybierz model","popover.assigned_to":"Przypisano do","popover.new_assignment":"+ nowe przypisanie","popover.open_in_devices":"Otwórz {name} w Urządzeniach","popover.triggers":"Wyzwalacze","popover.new_trigger":"+ nowy wyzwalacz","popover.any_receiver":"Dowolny odbiornik","popover.n_more":"{name} + {count} więcej","cmdrow.rename":"Kliknij, aby zmienić nazwę","cmdrow.tx_raw_on":"Odtwarza przechwycony kod Pronto. Kliknij, aby zamiast tego wysłać czyste, zdekodowane czasy pakietu.","cmdrow.tx_raw_off":"Wysyła czyste, zdekodowane czasy pakietu. Kliknij, aby zamiast tego odtworzyć przechwycony kod Pronto.","cmdrow.sends_times":"Wysyła to polecenie {count} razy","cmdrow.dittos":"Dołącza {count} powtórzeń ditto NEC","cmdrow.raw_timings":"RAW: {count} czasów","cmdrow.not_learned":"Jeszcze nie nauczono","cmdrow.edit_code":"Zobacz lub edytuj kod","cmdrow.map_action":"Przypisz mapowanie akcji","cmdrow.actions":"AKCJE","cmdrow.test":"Test","cmdrow.trigger":"Wyzwalacz","cmdrow.edit_trigger":"Edytuj wyzwalacz","cmdrow.create_trigger":"Utwórz wyzwalacz","cmdrow.delete":"Usuń","cmdrow.learn":"Ucz","trigger.alias_tag":"alias","trigger.event":"Zdarzenie wyzwalacza","trigger.edit_heading":"Edytuj wyzwalacz","trigger.create_heading":"Utwórz wyzwalacz","trigger.mirror_hint":"Uruchamia się, gdy ten sygnał przychodzi spoza Home Assistant (fizyczny pilot lub inna aplikacja), nigdy przy wysyłkach samego domu.","trigger.name_label":"Nazwa wyzwalacza","trigger.name_placeholder":"np. Zasilanie TV","trigger.min_hits":"Min. naciśnięć","trigger.min_hits_hint":"Liczba naciśnięć w ciągu 5s do uruchomienia","trigger.scope_hint":"Uruchamia się raz na naciśnięcie, niezależnie od tego, ile odbiorników w zakresie zaobserwuje sygnał.","trigger.save_failed":"Zapis nie powiódł się","common.saving":"Zapisywanie...","common.update":"Aktualizuj","common.create":"Utwórz","common.delete":"Usuń","assign.heading":"Przypisz sygnał","assign.hits":"{count} odbiorów","assign.mode_existing":"Istniejące urządzenie","assign.mode_new":"Nowe urządzenie","assign.send_times":"Liczba wysyłek","assign.send_times_hint":"Wysyła to polecenie tyle razy na naciśnięcie, dla urządzeń wymagających powtórzenia. Domyślnie 1.","assign.ditto_count":"Liczba ditto","assign.ditto_title":"Dołącza ramki powtórzeń po ramce głównej; niektóre rygorystyczne odbiorniki wymagają co najmniej jednej, aby zarejestrować polecenie.","assign.ditto_hint":"Dołącza ramki powtórzeń po ramce głównej; niektóre rygorystyczne odbiorniki wymagają co najmniej jednej, aby zarejestrować polecenie.","assign.assigning":"Przypisywanie...","assign.create_assign":"Utwórz i przypisz","assign.assign":"Przypisz","assign.target_device":"Urządzenie docelowe","assign.no_devices":'Brak urządzeń. Przełącz na "Nowe urządzenie", aby je utworzyć.',"assign.select_device":"Wybierz urządzenie...","assign.command_name":"Nazwa polecenia","assign.command_placeholder":"Wpisz nazwę polecenia","assign.select_command":"Wybierz polecenie...","assign.custom":"Niestandardowe...","assign.command_required":"Nazwa polecenia jest wymagana.","assign.target_required":"Wybierz urządzenie docelowe.","assign.failed_duplicate":"Przypisanie nie powiodło się. Sygnał może mieć zduplikowany kod na urządzeniu docelowym.","pluckdlg.blaster_required":"Wybierz nadajnik, z którego chcesz wyciągać.","pluckdlg.appliance_required":"Sprzęt jest wymagany.","pluckdlg.add_heading":"Dodaj nadajnik","pluckdlg.loading_blasters":"Ładowanie nadajników...","pluckdlg.pluck_from":"Wyciągnij z","pluckdlg.select_blaster":"Wybierz nadajnik","pluckdlg.appliance":"Sprzęt","pluckdlg.appliance_placeholder":"np. świece","pluckdlg.name_placeholder":"np. Świece w salonie","pluckdlg.signal_heading":"Wyciągnij sygnał","pluckdlg.pluck_failed":"Wyciąganie nie powiodło się.","pluckdlg.no_response":"Brak odpowiedzi z nadajnika. Spróbuj ponownie.","pluckdlg.recognized_as":"Rozpoznano jako {protocol}","pluckdlg.valid_pronto":"Prawidłowy kod Pronto","pluckdlg.command_help":"Nazwa nadana temu kodowi podczas uczenia w aplikacji producenta.","pluckdlg.command_placeholder":"np. pwr_on","pluckdlg.plucking":"Wyciąganie...","pluckdlg.pluck":"Wyciągnij","pluckdlg.captured":"Przechwycono","pluckdlg.remove_capture":"Usuń to przechwycenie","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Nie znaleziono zgodnych nadajników. Zainstaluj obsługiwaną integrację IR (np. Tuya Local) i najpierw naucz kod.","editor.ditto_disabled_cmd":"Liczba ditto działa, gdy polecenie jest wysyłane jako NEC. Przełącz pigułkę na NEC, aby włączyć.","editor.ditto_disabled":"Liczba ditto dotyczy zdekodowanych sygnałów (obecnie NEC). Surowe kody Pronto są wysyłane tak, jak je przechwycono.","editor.copied":"Skopiowano","editor.press_copy":"Naciśnij Cmd/Ctrl+C","editor.valid":"Prawidłowy kod Pronto","editor.not_valid":"Jeszcze nieprawidłowy","editor.burst_pair.one":"{count} para impulsów","editor.burst_pair.few":"{count} pary impulsów","editor.burst_pair.many":"{count} par impulsów","editor.burst_pair.other":"{count} pary impulsów","editor.recognized_as":"Rozpoznano jako {protocol}","editor.snap_notice":"Nośna wynosi {khz} kHz, poza standardami IR. Niektóre odbiorniki ją odrzucają.","editor.snapping":"Dopasowywanie...","editor.snap_to":"Dopasuj do {khz} kHz","editor.edit_command":"Edytuj polecenie","editor.edit_signal":"Edytuj sygnał","editor.create_signal":"Utwórz sygnał","common.save":"Zapisz","editor.trigger_note_cmd":"To polecenie ma wyzwalacz, który automatycznie się przestawi.","editor.trigger_note_sig":"Ten sygnał ma wyzwalacz, który automatycznie się przestawi.","editor.alias_label":"Alias","editor.alias_optional":"Alias (opcjonalnie)","editor.pronto_code":"Kod Pronto","editor.select_all":"Zaznacz wszystko (potem Cmd/Ctrl+C)","editor.alias_placeholder":"np. Zasilanie","editor.send_times_title":"Wysyła całe polecenie tyle razy jako niezależne naciśnięcia, dla urządzeń wymagających powtórzenia.","editor.ditto_title":"Dołącza ramki powtórzeń po ramce głównej. Niektóre rygorystyczne odbiorniki, zwłaszcza profesjonalny sprzęt audio, wymagają co najmniej jednej.","editor.observed.one":"Zaobserwowano przy przechwyceniu: {count} ditto","editor.observed.few":"Zaobserwowano przy przechwyceniu: {count} ditto","editor.observed.many":"Zaobserwowano przy przechwyceniu: {count} ditto","editor.observed.other":"Zaobserwowano przy przechwyceniu: {count} ditto","rel.just_now":"przed chwilą","mirror.via":"przez {name}","mirror.via_n":"przez {count} nadajników","mirror.not_heard":"nieusłyszany","mirror.heard_in":"ostatnio usłyszany w {areas}","mirror.heard_by":"ostatnio usłyszany przez {names}","mirror.chip_automation":"Wysyłka automatyzacji","mirror.chip_integration":"Wysyłka integracji","mirror.chip_test":"Ręczna wysyłka testowa","mirror.chip_device":"Urządzenie HAIR","mirror.chip_send":"Wysyłka","mirror.unknown_title":"Wysłano nieznany sygnał IR","mirror.unknown_hint":"{name} nadał, ale nic nie było na tyle blisko, by usłyszeć, co powiedział. Umieść odbiornik w zasięgu słuchu, aby złapać następną wysyłkę.","mirror.the_blaster":"Nadajnik","mirror.sent":"Wysłano!","mirror.sent_all_n":"Wysłano! ({sent}/{total})","mirror.sent_partial":"Wysłano ({sent}/{total})","mirror.failed":"Niepowodzenie","mirror.error":"Błąd","mirror.sending":"Wysyłanie...","mirror.test":"Test","mirror.stat_sends":"WYSYŁKI","mirror.stat_not_heard":"NIEUSŁYSZANE","mirror.stat_emitters":"NADAJNIKI","mirror.stat_signals":"SYGNAŁY","mirror.last_send_ago":"ostatnia wysyłka {rel} temu","mirror.last_send_just":"ostatnia wysyłka przed chwilą","mirror.no_receivers":"brak odbiorników","mirror.filter_all":"Wszystkie ({count})","mirror.filter_not_heard":"Nieusłyszane ({count})","mirror.search":"Szukaj wysyłek...","mirror.no_match":"Żadna wysyłka nie pasuje.","mirror.signals.one":"{count} sygnał","mirror.signals.few":"{count} sygnały","mirror.signals.many":"{count} sygnałów","mirror.signals.other":"{count} sygnału","mirror.sends_times":"Wysyła ten sygnał {count} razy","mirror.assign_disabled":"Tożsamość nieznana -- nic nie usłyszano w odpowiedzi do przypisania","mirror.assigned_one":"Przypisano do {device} / {command}","mirror.assigned_n":"Przypisano do {count} poleceń:","mirror.assign_title":"Przypisz ten sygnał do urządzenia HAIR","mirror.test_title":"Wyślij ten sygnał przez nadajnik, aby go przetestować","mirror.test_disabled":"Tożsamość nieznana -- nie ma czego wysłać","mirror.trigger_disabled":"Tożsamość nieznana -- nie ma czego powiązać","mirror.trigger_edit":"Edytuj wyzwalacz(e) tego sygnału","mirror.trigger_create":"Uruchamia się, gdy ten sygnał przychodzi spoza Home Assistant","mirror.delete_title":"Wyczyść ten wpis (wróci przy następnej wysyłce)","mirror.empty_title":"Jeszcze niczego nie wysłano","mirror.empty_sub":"Polecenia wysyłane przez urządzenia HAIR, automatyzacje lub dowolną integrację platformy podczerwieni pojawią się tutaj, wraz z celem i tym, kto je usłyszał.","mirror.del_trigger_title":"Usuń wyzwalacz","mirror.del_trigger_msg":"Usunąć ten wyzwalacz na stałe? Automatyzacje, które go używają, przestaną się uruchamiać.","mirror.clear_title":"Wyczyść wpis Mirror","mirror.clear_msg":"Usunąć ten wpis z Mirror? Wróci przy następnej wysyłce tego sygnału.","common.delete_failed":"Usuwanie nie powiodło się: {message}","device_type.other_card":"Urządzenie IR","devlist.loading":"Ładowanie urządzeń IR...","devlist.empty_title":"Brak urządzeń IR","devlist.empty_sub":"Dodaj pierwsze urządzenie, aby zacząć.","devlist.add_device_plus":"+ Dodaj urządzenie","devlist.title":"Urządzenia HAIR","devlist.add_device":"Dodaj urządzenie","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Brak TX","devlist.rx_native_title":"Odbiera przez natywną platformę podczerwieni HA","devlist.rx_bridge_active":"Stary mostek jest nadal aktywny. Natywny odbiornik go zastępuje -- możesz usunąć blok on_pronto: z konfiguracji ESPHome.","devlist.rx_bridge_title":"Odbiera przez stary mostek zdarzeń ESPHome","devlist.rx_upgrade_title":"Zaktualizuj do HA 2026.6+, aby uzyskać natywną obsługę odbiorników","devlist.tx_native_title":"Wysyła przez natywną platformę podczerwieni HA","devlist.blasters":"Nadajniki (do wyciągania)","devlist.emitters":"Nadajniki","devlist.receivers":"Odbiorniki","devlist.proxies":"Proxy","devlist.hits_badge":"{count}x odbiorów","devlist.on":"WŁ","devlist.off":"WYŁ","devlist.delete_trigger":"Usuń wyzwalacz","devlist.delete_device":"Usuń urządzenie","devlist.open_plucker_title":"Otwórz w Plucker","devlist.open_plucker":"Otwórz w Plucker","devlist.del_trigger_msg":'Usunąć "{name}"? Powiązana encja zdarzenia HA również zostanie usunięta.',"devlist.del_device_title":"Usuń urządzenie","devlist.del_device_msg":'Usunąć "{name}"? Polecenia, mapowania akcji i przypisania nadajników zostaną usunięte. Wyzwalacze pozostaną nietknięte.',"common.close":"Zamknij","devdetail.name_updated":"Zaktualizowano nazwę","devdetail.type_updated":"Zaktualizowano typ urządzenia","devdetail.emitters_updated":"Zaktualizowano nadajniki","devdetail.update_failed":"Aktualizacja nie powiodła się: {message}","devdetail.reorder_failed":"Zmiana kolejności nie powiodła się: {message}","devdetail.mapped_to":"Zmapowano na {action}","devdetail.mapping_cleared":"Mapowanie wyczyszczone","devdetail.mapping_failed":"Mapowanie nie powiodło się: {message}","devdetail.sent_cmd":'Wysłano "{name}"',"devdetail.send_failed":"Wysyłanie nie powiodło się: {message}","devdetail.cmd_updated":"Zaktualizowano polecenie","devdetail.cmd_updated_repointed":"Zaktualizowano polecenie. Przestawiono wyzwalacz {names}.","devdetail.rename_failed":"Zmiana nazwy nie powiodła się: {message}","devdetail.removed":'Usunięto "{name}"',"devdetail.saved":'Zapisano "{name}"',"devdetail.type":"Typ","devdetail.commands":"Polecenia ({count})","devdetail.no_commands":"Brak poleceń. Dodaj jedno poniżej.","devdetail.drag":"Przeciągnij, aby zmienić kolejność","devdetail.map_action":"Mapuj akcję","devdetail.none_clear":"Brak (wyczyść)","devdetail.sniff_title":"Przechwyć nowy sygnał w zakładce Sniffer","devdetail.sniffed":"+ Sygnał ze Sniffera","devdetail.clip_title":"Wklej nowy sygnał w zakładce Clips","devdetail.clipped":"+ Wklejony sygnał","devdetail.mirror_title":"Podsłuchaj wysyłkę w zakładce Mirror","devdetail.mirrored":"+ Sygnał z Mirror","devdetail.del_device_title":"Usunąć {name}?","devdetail.del_device_msg":"To usuwa wszystkie przechwycone polecenia i automatycznie utworzoną encję. Tej operacji nie można cofnąć.","devdetail.del_cmd_title":"Usunąć polecenie?","devdetail.del_cmd_msg":'Usunąć "{name}"? Nie można tego cofnąć.',"devdetail.del_trigger_msg":"Usunąć ten wyzwalacz? Powiązana encja zdarzenia HA również zostanie usunięta.","rel.min_ago":"{count} min temu","rel.h_ago":"{count} godz. temu","rel.d_ago":"{count} dni temu","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} pilot","sniffer.remotes.few":"{count} piloty","sniffer.remotes.many":"{count} pilotów","sniffer.remotes.other":"{count} pilota","sniffer.scanning":"Skanowanie sygnałów...","sniffer.empty_title":"Nie wykryto nieznanych sygnałów","sniffer.empty_body":"Gdy urządzenia ESPHome odbiorą nierozpoznane sygnały IR, pojawią się tutaj automatycznie.","sniffer.empty_hint":"Naciśnij przycisk pilota, który nie został jeszcze skonfigurowany.","sniffer.norx_title":"Nie skonfigurowano odbiornika IR","sniffer.norx_body":"HAIR nie ma jeszcze jak odbierać sygnałów IR, więc Sniffer nie może niczego przechwycić.","sniffer.norx_hint":"Skonfiguruj odbiornik ESPHome z platformą podczerwieni lub sprawdź w Ustawienia, potem Urządzenia i usługi, czy urządzenie IR zostało dodane.","sniffer.show_dismissed_title":"Przywróć wcześniej ukryte piloty","sniffer.show_dismissed":"Pokaż odrzucone","sniffer.hide_dismissed":"Ukryj odrzucone","sniffer.clear_all_title":"Czyści cały katalog nieznanych ORAZ listę odrzuconych. Użyj Pokaż odrzucone przed Wyczyść wszystko, jeśli chcesz zachować pojedyncze odrzucone wpisy.","sniffer.clear_all":"Wyczyść wszystko","sniffer.del_signal_title":"Usuń sygnał","sniffer.del_signal_msg":"Usunąć ten sygnał na stałe? Nie można tego cofnąć.","sniffer.clear_all_confirm_title":"Wyczyść wszystkie sygnały","sniffer.clear_all_confirm_msg":"Usunąć wszystkie nieznane sygnały i urządzenia? Nie można tego cofnąć.","sniffer.hair_device":"Urządzenie HAIR","sniffer.promote":"Awansuj","sniffer.dismissed":"odrzucony","sniffer.restore":"Przywróć","sniffer.dismiss":"Odrzuć","sniffer.addr":"adres: {address}","sniffer.signals_head":"Sygnały ({count})","sniffer.first_seen":"Pierwszy odbiór: {time}","sniffer.restore_first":"Najpierw przywróć tego pilota","sniffer.trigger_create":"Utwórz encję zdarzenia HA uruchamianą tym sygnałem","common.raw":"RAW","sniffer.hit_word.one":"odbiór","sniffer.hit_word.few":"odbiory","sniffer.hit_word.many":"odbiorów","sniffer.hit_word.other":"odbioru","sniffer.signal_word.one":"sygnał","sniffer.signal_word.few":"sygnały","sniffer.signal_word.many":"sygnałów","sniffer.signal_word.other":"sygnału","common.loading_plain":"Ładowanie...","clips.title":"HAIR Clipper","clips.add_remote":"+ Dodaj pilota","clips.empty_title":"Brak wirtualnych pilotów","clips.empty_body":"Clipper pozwala tworzyć piloty przez wklejanie kodów Pronto. Utwórz pilota, potem dodaj sygnał dla każdego przycisku.","clips.empty_hint":'Kliknij "+ Dodaj pilota" powyżej, aby zacząć wklejanego pilota.',"clips.clear_all_title":"Usuwa wszystkie wklejone piloty i ich sygnały. Przechwycone sygnały pozostają nietknięte.","clips.remote_fallback":"Pilot","clips.add_signal_title":"Dodaj sygnał do tego pilota","clips.add_signal":"+ Dodaj sygnał","clips.no_signals":'Brak sygnałów. Kliknij "+ Dodaj sygnał", aby wkleić kod Pronto.',"clips.delete_remote_title":"Usuń tego pilota i wszystkie jego sygnały","clips.delete_remote":"Usuń pilota","clips.test_title":"Wyślij ten sygnał przez nadajnik","clips.clear_all_confirm_title":"Wyczyść wszystkie klipy","clips.clear_all_confirm_msg":"Usunąć wszystkie wklejone piloty i ich sygnały? Nie można tego cofnąć. Przechwycone sygnały pozostaną nietknięte.","clips.del_remote_confirm_title":"Usuń pilota","clips.del_remote_msg_n.one":'Usunąć "{name}" i jego {count} sygnał? Nie można tego cofnąć.',"clips.del_remote_msg_n.few":'Usunąć "{name}" i jego {count} sygnały? Nie można tego cofnąć.',"clips.del_remote_msg_n.many":'Usunąć "{name}" i jego {count} sygnałów? Nie można tego cofnąć.',"clips.del_remote_msg_n.other":'Usunąć "{name}" i jego {count} sygnału? Nie można tego cofnąć.',"clips.del_remote_msg":'Usunąć "{name}"? Nie można tego cofnąć.',"pluck.vendor_unavailable":"Integracja tego nadajnika jest obecnie niedostępna. Upewnij się, że integracja producenta jest załadowana.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Dodaj nadajnik","pluck.empty_title":"Brak wyciągniętych nadajników","pluck.empty_body":"Plucker importuje kody IR z istniejących nadajników, aby używać ich w HAIR bez ponownego uczenia każdego z nich.","pluck.empty_hint":'Kliknij "+ Dodaj nadajnik" powyżej, aby odbić nadajnik.',"pluck.clear_all_title":"Usuwa wszystkie wyciągnięte nadajniki i ich sygnały. Przechwycone i wklejone sygnały pozostają nietknięte.","pluck.blaster_fallback":"Nadajnik","pluck.promote_title":"Utwórz urządzenie HAIR z tego nadajnika","pluck.pluck_signal_title":"Wyciągnij kod z tego nadajnika","pluck.pluck_signal":"+ Wyciągnij sygnał","pluck.no_signals":'Brak sygnałów. Kliknij "+ Wyciągnij sygnał", aby pobrać kod z tego nadajnika.',"pluck.delete_blaster_title":"Usuń ten nadajnik i wszystkie jego sygnały","pluck.delete_blaster":"Usuń nadajnik","pluck.clear_all_confirm_title":"Wyczyść wszystkie wyciągnięte","pluck.clear_all_confirm_msg":"Usunąć wszystkie wyciągnięte nadajniki i ich sygnały? Nie można tego cofnąć. Przechwycone i wklejone sygnały pozostaną nietknięte.","pluck.del_blaster_confirm_title":"Usuń nadajnik","devdetail.custom_action":"Niestandardowa...","devdetail.custom_action_placeholder":"np. temp_30","devdetail.set":"Ustaw","vocab.back_return":"Wstecz","vocab.brightness_down":"Jasność -","vocab.brightness_up":"Jasność +","vocab.channel_down":"Kanał -","vocab.channel_up":"Kanał +","vocab.close":"Zamknij","vocab.color_temp_cooler":"Zimniejsza biel","vocab.color_temp_warmer":"Cieplejsza biel","vocab.down":"Dół","vocab.fan_auto":"Wentylator: Auto","vocab.fan_high":"Wentylator: Wysoki","vocab.fan_low":"Wentylator: Niski","vocab.fan_medium":"Wentylator: Średni","vocab.fast_forward":"Przewiń do przodu","vocab.guide":"Przewodnik","vocab.left":"Lewo","vocab.menu":"Menu","vocab.mode_auto":"Tryb: Auto","vocab.mode_cool":"Tryb: Chłodzenie","vocab.mode_dry":"Tryb: Osuszanie","vocab.mode_fan":"Tryb: Wentylacja","vocab.mode_heat":"Tryb: Grzanie","vocab.mute":"Wycisz","vocab.off":"Wyłączony","vocab.on":"Włączony","vocab.open":"Otwórz","vocab.oscillate":"Oscylacja","vocab.pause":"Pauza","vocab.play":"Odtwarzaj","vocab.power":"Zasilanie","vocab.power_off":"Wyłącz","vocab.power_on":"Włącz","vocab.power_toggle":"Przełącz zasilanie","vocab.rewind":"Przewiń do tyłu","vocab.right":"Prawo","vocab.select_ok":"Wybierz/OK","vocab.source_input":"Źródło/Wejście","vocab.speed_down":"Prędkość -","vocab.speed_up":"Prędkość +","vocab.stop":"Stop","vocab.swing_toggle":"Ruch żaluzji","vocab.timer":"Minutnik","vocab.up":"Góra","vocab.volume_down":"Głośność -","vocab.volume_up":"Głośność +"},pt:{"_meta.review":"Programming-assistant draft (2026-07-19), Brazilian-leaning Portuguese, not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Carregando…","panel.load_failed":"Falha ao carregar os dispositivos: {message}","panel.open_menu":"Abrir menu","panel.tab.devices":"Dispositivos","panel.tagline.devices":"Gerencie seus dispositivos IR e o hardware que os controla.","panel.tagline.sniffer":"Capture códigos IR ao vivo, direto do ar.","panel.tagline.clips":"Monte controles remotos colando códigos IR conhecidos.","panel.tagline.plucker":"Extraia códigos IR dos seus emissores existentes.","panel.tagline.mirror":"Veja ao vivo as transmissões infravermelhas do Home Assistant.","common.confirm":"Confirmar","common.cancel":"Cancelar","common.are_you_sure":"Tem certeza?","common.remove":"Remover","alias.placeholder":"Apelido para este sinal","alias.tag":"apelido","alias.clear":"Limpar apelido","alias.edit":"Clique para editar o apelido","alias.name":"Clique para nomear este sinal","picker.emitters_label":"Emissores IR","picker.add_emitter":"+ Adicionar emissor...","picker.no_emitters":"Nenhum emissor IR encontrado.","picker.all_emitters_selected":"Todos os emissores selecionados.","picker.receivers_label":"Via receptor(es):","picker.add_receiver":"+ Adicionar receptor...","picker.no_receivers":"Nenhum receptor IR encontrado.","picker.all_receivers_selected":"Todos os receptores selecionados.","device_type.media_player":"Reprodutor de mídia","device_type.ac":"Ar-condicionado","device_type.fan":"Ventilador","device_type.light":"Luz","device_type.switch":"Interruptor","device_type.screen":"Tela / Persiana","device_type.other":"Outro","common.name":"Nome","common.device_type":"Tipo de dispositivo","common.name_required":"O nome é obrigatório.","common.creating":"Criando...","common.device_name_placeholder":"ex. TV da sala","promote.heading":"Promover a dispositivo","promote.device_name":"Nome do dispositivo","promote.device_name_required":"O nome do dispositivo é obrigatório.","promote.emitter_required":"Selecione pelo menos um emissor IR.","promote.create_device":"Criar dispositivo","adddev.heading":"Adicionar dispositivo","adddev.emitter_required":"Escolha pelo menos um emissor IR.","adddev.create":"Criar","dup.heading":"Duplicar dispositivo","dup.hint_duplicating":"Duplicando {name}.","dup.hint_body":"O novo dispositivo recebe uma cópia de cada comando, mapeamento de ação e atribuição de emissor. Você pode mudar tudo depois.","dup.duplicating":"Duplicando...","dup.duplicate":"Duplicar","promote.description":"Crie um novo dispositivo HAIR. Depois você pode atribuir sinais capturados a ele como comandos.","capture.listening":"Aguardando sinal IR…","capture.instruction":'Aponte o controle remoto para o receptor IR e pressione o botão "{name}".',"capture.remaining":"{seconds}s restantes","capture.captured":"Sinal capturado!","capture.protocol":"Protocolo: {protocol}","capture.protocol_raw":"Bruto","capture.verify":"Funcionou? Pressione Testar para verificar.","capture.test":"▶ Testar","capture.recapture":"↻ Recapturar","capture.save_next":"Salvar e aprender o próximo ▶▶","capture.no_signal":"⚠ Nenhum sinal detectado","capture.tip_point":"Aponte o controle diretamente para o receptor IR","capture.tip_closer":"Aproxime-se (a menos de 1 metro)","capture.tip_hold":"Segure o botão pressionado por um instante","capture.try_again":"↻ Tentar novamente","capture.duplicate":"⚠ Sinal duplicado detectado","capture.duplicate_instruction":'Este sinal corresponde ao seu comando "{name}". Alguns controles usam o mesmo sinal para vários botões.',"capture.recapture_different":"Recapturar outro","capture.save_anyway":"Salvar mesmo assim","capture.error":"⚠ Erro de captura","capture.learning":'Aprendendo: "{name}"',"test_emitter.heading":"Enviar de","test_emitter.sending":"Enviando...","test_emitter.send":"Enviar","createremote.heading":"Criar controle remoto","createremote.type":"Tipo","createremote.blank":"Controle em branco","createremote.from_library":"Da biblioteca de códigos","createremote.model":"Modelo","createremote.select_model":"Selecione um modelo","popover.assigned_to":"Atribuído a","popover.new_assignment":"+ nova atribuição","popover.open_in_devices":"Abrir {name} em Dispositivos","popover.triggers":"Gatilhos","popover.new_trigger":"+ novo gatilho","popover.any_receiver":"Qualquer receptor","popover.n_more":"{name} + {count} mais","cmdrow.rename":"Clique para renomear","cmdrow.tx_raw_on":"Reproduz o Pronto capturado. Clique para transmitir em vez disso os tempos de pacote decodificados e limpos.","cmdrow.tx_raw_off":"Transmite os tempos de pacote decodificados e limpos. Clique para reproduzir em vez disso o Pronto capturado.","cmdrow.sends_times":"Envia este comando {count} vezes","cmdrow.dittos":"Anexa {count} dittos NEC","cmdrow.raw_timings":"BRUTO: {count} tempos","cmdrow.not_learned":"Ainda não aprendido","cmdrow.edit_code":"Ver ou editar o código","cmdrow.map_action":"Atribuir mapeamento de ação","cmdrow.actions":"AÇÕES","cmdrow.test":"Testar","cmdrow.trigger":"Gatilho","cmdrow.edit_trigger":"Editar gatilho","cmdrow.create_trigger":"Criar gatilho","cmdrow.delete":"Excluir","cmdrow.learn":"Aprender","trigger.alias_tag":"apelido","trigger.event":"Evento do gatilho","trigger.edit_heading":"Editar gatilho","trigger.create_heading":"Criar gatilho","trigger.mirror_hint":"Dispara quando este sinal chega de fora do Home Assistant (um controle físico ou outro aplicativo), nunca com os envios da própria casa.","trigger.name_label":"Nome do gatilho","trigger.name_placeholder":"ex. Ligar TV","trigger.min_hits":"Toques mín","trigger.min_hits_hint":"Número de toques em 5s para disparar","trigger.scope_hint":"Dispara uma vez por toque, não importa quantos receptores no escopo observem o sinal.","trigger.save_failed":"Falha ao salvar","common.saving":"Salvando...","common.update":"Atualizar","common.create":"Criar","common.delete":"Excluir","assign.heading":"Atribuir sinal","assign.hits":"{count} recepções","assign.mode_existing":"Dispositivo existente","assign.mode_new":"Novo dispositivo","assign.send_times":"Número de envios","assign.send_times_hint":"Transmite este comando essa quantidade de vezes por toque, para dispositivos que precisam de repetição. Padrão 1.","assign.ditto_count":"Número de dittos","assign.ditto_title":"Anexa quadros de repetição após o quadro principal; alguns receptores rigorosos exigem pelo menos um para registrar o comando.","assign.ditto_hint":"Anexa quadros de repetição após o quadro principal; alguns receptores rigorosos exigem pelo menos um para registrar o comando.","assign.assigning":"Atribuindo...","assign.create_assign":"Criar e atribuir","assign.assign":"Atribuir","assign.target_device":"Dispositivo de destino","assign.no_devices":'Nenhum dispositivo ainda. Mude para "Novo dispositivo" para criar um.',"assign.select_device":"Selecione um dispositivo...","assign.command_name":"Nome do comando","assign.command_placeholder":"Digite o nome do comando","assign.select_command":"Selecione um comando...","assign.custom":"Personalizado...","assign.command_required":"O nome do comando é obrigatório.","assign.target_required":"Selecione um dispositivo de destino.","assign.failed_duplicate":"Falha na atribuição. O sinal pode ter um código duplicado no dispositivo de destino.","pluckdlg.blaster_required":"Escolha um emissor de onde extrair.","pluckdlg.appliance_required":"O equipamento é obrigatório.","pluckdlg.add_heading":"Adicionar emissor","pluckdlg.loading_blasters":"Carregando emissores...","pluckdlg.pluck_from":"Extrair de","pluckdlg.select_blaster":"Selecione um emissor","pluckdlg.appliance":"Equipamento","pluckdlg.appliance_placeholder":"ex. velas","pluckdlg.name_placeholder":"ex. Velas da sala","pluckdlg.signal_heading":"Extrair sinal","pluckdlg.pluck_failed":"Falha na extração.","pluckdlg.no_response":"Sem resposta do emissor. Tente novamente.","pluckdlg.recognized_as":"Reconhecido como {protocol}","pluckdlg.valid_pronto":"Código Pronto válido","pluckdlg.command_help":"O nome que você deu a este código quando o aprendeu no aplicativo do fabricante.","pluckdlg.command_placeholder":"ex. pwr_on","pluckdlg.plucking":"Extraindo...","pluckdlg.pluck":"Extrair","pluckdlg.captured":"Capturado","pluckdlg.remove_capture":"Remover esta captura","pluckdlg.alias":"Apelido","pluckdlg.no_blasters":"Nenhum emissor compatível encontrado. Instale uma integração IR compatível (como Tuya Local) e aprenda um código primeiro.","editor.ditto_disabled_cmd":"O número de dittos vale quando o comando é transmitido como NEC. Mude a pílula para NEC para ativar.","editor.ditto_disabled":"O número de dittos vale para sinais decodificados (NEC hoje). Códigos Pronto brutos são transmitidos como capturados.","editor.copied":"Copiado","editor.press_copy":"Pressione Cmd/Ctrl+C","editor.valid":"Código Pronto válido","editor.not_valid":"Ainda não é válido","editor.burst_pair.one":"{count} par de pulsos","editor.burst_pair.other":"{count} pares de pulsos","editor.recognized_as":"Reconhecido como {protocol}","editor.snap_notice":"A portadora está em {khz} kHz, fora dos padrões IR. Alguns receptores a rejeitam.","editor.snapping":"Ajustando...","editor.snap_to":"Ajustar para {khz} kHz","editor.edit_command":"Editar comando","editor.edit_signal":"Editar sinal","editor.create_signal":"Criar sinal","common.save":"Salvar","editor.trigger_note_cmd":"Este comando tem um gatilho que se redirecionará automaticamente.","editor.trigger_note_sig":"Este sinal tem um gatilho que se redirecionará automaticamente.","editor.alias_label":"Apelido","editor.alias_optional":"Apelido (opcional)","editor.pronto_code":"Código Pronto","editor.select_all":"Selecionar tudo (depois Cmd/Ctrl+C)","editor.alias_placeholder":"ex. Ligar","editor.send_times_title":"Transmite o comando inteiro essa quantidade de vezes como toques independentes, para dispositivos que precisam de repetição.","editor.ditto_title":"Anexa quadros de repetição após o quadro principal. Alguns receptores rigorosos, principalmente equipamentos de áudio profissionais, exigem pelo menos um.","editor.observed.one":"Observado na captura: {count} ditto","editor.observed.other":"Observado na captura: {count} dittos","rel.just_now":"agora mesmo","mirror.via":"via {name}","mirror.via_n":"via {count} emissores","mirror.not_heard":"não ouvido","mirror.heard_in":"ouvido pela última vez em {areas}","mirror.heard_by":"ouvido pela última vez por {names}","mirror.chip_automation":"Envio de automação","mirror.chip_integration":"Envio de integração","mirror.chip_test":"Envio de teste manual","mirror.chip_device":"Dispositivo HAIR","mirror.chip_send":"Envio","mirror.unknown_title":"Sinal IR desconhecido enviado","mirror.unknown_hint":"{name} disparou, mas nada estava perto o bastante para ouvir o que ele disse. Coloque um receptor ao alcance para captar o próximo envio.","mirror.the_blaster":"O emissor","mirror.sent":"Enviado!","mirror.sent_all_n":"Enviado! ({sent}/{total})","mirror.sent_partial":"Enviado ({sent}/{total})","mirror.failed":"Falhou","mirror.error":"Erro","mirror.sending":"Enviando...","mirror.test":"Testar","mirror.stat_sends":"ENVIOS","mirror.stat_not_heard":"NÃO OUVIDOS","mirror.stat_emitters":"EMISSORES","mirror.stat_signals":"SINAIS","mirror.last_send_ago":"último envio há {rel}","mirror.last_send_just":"último envio agora mesmo","mirror.no_receivers":"sem receptores","mirror.filter_all":"Todos ({count})","mirror.filter_not_heard":"Não ouvidos ({count})","mirror.search":"Buscar envios...","mirror.no_match":"Nenhum envio corresponde.","mirror.signals.one":"{count} sinal","mirror.signals.other":"{count} sinais","mirror.sends_times":"Envia este sinal {count} vezes","mirror.assign_disabled":"Identidade desconhecida -- nada foi ouvido de volta para atribuir","mirror.assigned_one":"Atribuído a {device} / {command}","mirror.assigned_n":"Atribuído a {count} comandos:","mirror.assign_title":"Atribuir este sinal a um dispositivo HAIR","mirror.test_title":"Enviar este sinal por um emissor para testá-lo","mirror.test_disabled":"Identidade desconhecida -- nada para enviar","mirror.trigger_disabled":"Identidade desconhecida -- nada para vincular","mirror.trigger_edit":"Editar gatilho(s) deste sinal","mirror.trigger_create":"Dispara quando este sinal chega de fora do Home Assistant","mirror.delete_title":"Limpar esta entrada (ela volta no próximo envio)","mirror.empty_title":"Nada enviado ainda","mirror.empty_sub":"Comandos enviados por dispositivos HAIR, automações ou qualquer integração da plataforma infravermelha aparecerão aqui, com o destino e quem os ouviu.","mirror.del_trigger_title":"Excluir gatilho","mirror.del_trigger_msg":"Excluir este gatilho permanentemente? As automações que o usam deixarão de disparar.","mirror.clear_title":"Limpar entrada do Mirror","mirror.clear_msg":"Remover esta entrada do Mirror? Ela voltará na próxima vez que este sinal for enviado.","common.delete_failed":"Falha ao excluir: {message}","device_type.other_card":"Dispositivo IR","devlist.loading":"Carregando dispositivos IR...","devlist.empty_title":"Nenhum dispositivo IR ainda","devlist.empty_sub":"Adicione seu primeiro dispositivo para começar.","devlist.add_device_plus":"+ Adicionar dispositivo","devlist.title":"Dispositivos HAIR","devlist.add_device":"Adicionar dispositivo","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Sem TX","devlist.rx_native_title":"Recebe pela plataforma infravermelha nativa do HA","devlist.rx_bridge_active":"A ponte legada ainda está ativa. O receptor nativo a substitui -- você pode remover o bloco on_pronto: da sua configuração ESPHome.","devlist.rx_bridge_title":"Recebe pela ponte legada de eventos do ESPHome","devlist.rx_upgrade_title":"Atualize para o HA 2026.6+ para suporte nativo a receptores","devlist.tx_native_title":"Envia pela plataforma infravermelha nativa do HA","devlist.blasters":"Emissores (extraíveis)","devlist.emitters":"Emissores","devlist.receivers":"Receptores","devlist.proxies":"Proxies","devlist.hits_badge":"{count}x recepções","devlist.on":"LIG","devlist.off":"DESL","devlist.delete_trigger":"Excluir gatilho","devlist.delete_device":"Excluir dispositivo","devlist.open_plucker_title":"Abrir no Plucker","devlist.open_plucker":"Abrir no Plucker","devlist.del_trigger_msg":'Remover "{name}"? A entidade de evento do HA associada também será removida.',"devlist.del_device_title":"Excluir dispositivo","devlist.del_device_msg":'Remover "{name}"? Comandos, mapeamentos de ação e atribuições de emissor serão excluídos. Os gatilhos não são afetados.',"common.close":"Fechar","devdetail.name_updated":"Nome atualizado","devdetail.type_updated":"Tipo de dispositivo atualizado","devdetail.emitters_updated":"Emissores atualizados","devdetail.update_failed":"Falha ao atualizar: {message}","devdetail.reorder_failed":"Falha ao reordenar: {message}","devdetail.mapped_to":"Mapeado para {action}","devdetail.mapping_cleared":"Mapeamento limpo","devdetail.mapping_failed":"Falha no mapeamento: {message}","devdetail.sent_cmd":'"{name}" enviado',"devdetail.send_failed":"Falha ao enviar: {message}","devdetail.cmd_updated":"Comando atualizado","devdetail.cmd_updated_repointed":"Comando atualizado. Gatilho {names} redirecionado.","devdetail.rename_failed":"Falha ao renomear: {message}","devdetail.removed":'"{name}" removido',"devdetail.saved":'"{name}" salvo',"devdetail.type":"Tipo","devdetail.commands":"Comandos ({count})","devdetail.no_commands":"Nenhum comando ainda. Adicione um abaixo.","devdetail.drag":"Arraste para reordenar","devdetail.map_action":"Mapear ação","devdetail.none_clear":"Nenhuma (limpar)","devdetail.sniff_title":"Capturar um novo sinal no Sniffer","devdetail.sniffed":"+ Sinal farejado","devdetail.clip_title":"Colar um novo sinal em Clips","devdetail.clipped":"+ Sinal colado","devdetail.mirror_title":"Escutar um envio no Mirror","devdetail.mirrored":"+ Sinal do Mirror","devdetail.del_device_title":"Excluir {name}?","devdetail.del_device_msg":"Isso remove todos os comandos capturados e a entidade criada automaticamente. Esta ação não pode ser desfeita.","devdetail.del_cmd_title":"Excluir comando?","devdetail.del_cmd_msg":'Remover "{name}"? Isso não pode ser desfeito.',"devdetail.del_trigger_msg":"Remover este gatilho? A entidade de evento do HA associada também será removida.","rel.min_ago":"há {count} min","rel.h_ago":"há {count}h","rel.d_ago":"há {count}d","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} controle","sniffer.remotes.other":"{count} controles","sniffer.scanning":"Procurando sinais...","sniffer.empty_title":"Nenhum sinal desconhecido detectado","sniffer.empty_body":"Quando seus dispositivos ESPHome receberem sinais IR não reconhecidos, eles aparecerão aqui automaticamente.","sniffer.empty_hint":"Experimente apertar um botão de um controle que ainda não foi configurado.","sniffer.norx_title":"Nenhum receptor IR configurado","sniffer.norx_body":"O HAIR ainda não tem como receber sinais IR, então o Sniffer não pode capturar nada.","sniffer.norx_hint":"Configure um receptor ESPHome com a plataforma infravermelha, ou verifique em Configurações, depois Dispositivos e serviços, se o seu dispositivo IR foi adotado.","sniffer.show_dismissed_title":"Restaurar controles ocultados anteriormente","sniffer.show_dismissed":"Mostrar descartados","sniffer.hide_dismissed":"Ocultar descartados","sniffer.clear_all_title":"Limpa todo o catálogo de desconhecidos E a lista de descartados. Use Mostrar descartados antes de Limpar tudo se quiser manter entradas descartadas individuais.","sniffer.clear_all":"Limpar tudo","sniffer.del_signal_title":"Excluir sinal","sniffer.del_signal_msg":"Excluir este sinal permanentemente? Isso não pode ser desfeito.","sniffer.clear_all_confirm_title":"Limpar todos os sinais","sniffer.clear_all_confirm_msg":"Remover todos os sinais e dispositivos desconhecidos? Isso não pode ser desfeito.","sniffer.hair_device":"Dispositivo HAIR","sniffer.promote":"Promover","sniffer.dismissed":"descartado","sniffer.restore":"Restaurar","sniffer.dismiss":"Descartar","sniffer.addr":"end: {address}","sniffer.signals_head":"Sinais ({count})","sniffer.first_seen":"Visto pela primeira vez: {time}","sniffer.restore_first":"Restaure este controle primeiro","sniffer.trigger_create":"Criar uma entidade de evento do HA que dispara com este sinal","common.raw":"BRUTO","sniffer.hit_word.one":"recepção","sniffer.hit_word.other":"recepções","sniffer.signal_word.one":"sinal","sniffer.signal_word.other":"sinais","common.loading_plain":"Carregando...","clips.title":"HAIR Clipper","clips.add_remote":"+ Adicionar controle","clips.empty_title":"Nenhum controle virtual ainda","clips.empty_body":"O Clipper permite montar controles remotos colando códigos Pronto. Crie um controle e depois adicione um sinal para cada botão.","clips.empty_hint":'Clique em "+ Adicionar controle" acima para começar um controle colado.',"clips.clear_all_title":"Exclui todos os controles colados e seus sinais. Os sinais farejados não são tocados.","clips.remote_fallback":"Controle","clips.add_signal_title":"Adicionar um sinal a este controle","clips.add_signal":"+ Adicionar sinal","clips.no_signals":'Nenhum sinal ainda. Clique em "+ Adicionar sinal" para colar um código Pronto.',"clips.delete_remote_title":"Excluir este controle e todos os seus sinais","clips.delete_remote":"Excluir controle","clips.test_title":"Enviar este sinal por um emissor","clips.clear_all_confirm_title":"Limpar todos os clips","clips.clear_all_confirm_msg":"Remover todos os controles colados e seus sinais? Isso não pode ser desfeito. Os sinais farejados não são afetados.","clips.del_remote_confirm_title":"Excluir controle","clips.del_remote_msg_n.one":'Remover "{name}" e seu {count} sinal? Isso não pode ser desfeito.',"clips.del_remote_msg_n.other":'Remover "{name}" e seus {count} sinais? Isso não pode ser desfeito.',"clips.del_remote_msg":'Remover "{name}"? Isso não pode ser desfeito.',"pluck.vendor_unavailable":"A integração deste emissor não está disponível no momento. Verifique se a integração do fabricante está carregada.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Adicionar emissor","pluck.empty_title":"Nenhum emissor extraído ainda","pluck.empty_body":"O Plucker importa códigos IR dos seus emissores existentes para usá-los no HAIR sem reaprender cada um.","pluck.empty_hint":'Clique em "+ Adicionar emissor" acima para espelhar um emissor.',"pluck.clear_all_title":"Exclui todos os emissores extraídos e seus sinais. Os sinais farejados e colados não são tocados.","pluck.blaster_fallback":"Emissor","pluck.promote_title":"Criar um dispositivo HAIR a partir deste emissor","pluck.pluck_signal_title":"Extrair um código deste emissor","pluck.pluck_signal":"+ Extrair sinal","pluck.no_signals":'Nenhum sinal ainda. Clique em "+ Extrair sinal" para puxar um código deste emissor.',"pluck.delete_blaster_title":"Excluir este emissor e todos os seus sinais","pluck.delete_blaster":"Excluir emissor","pluck.clear_all_confirm_title":"Limpar todos os extraídos","pluck.clear_all_confirm_msg":"Remover todos os emissores extraídos e seus sinais? Isso não pode ser desfeito. Os sinais farejados e colados não são afetados.","pluck.del_blaster_confirm_title":"Excluir emissor","devdetail.custom_action":"Personalizado...","devdetail.custom_action_placeholder":"ex. temp_30","devdetail.set":"Definir","vocab.back_return":"Voltar","vocab.brightness_down":"Brilho -","vocab.brightness_up":"Brilho +","vocab.channel_down":"Canal -","vocab.channel_up":"Canal +","vocab.close":"Fechar","vocab.color_temp_cooler":"Branco mais frio","vocab.color_temp_warmer":"Branco mais quente","vocab.down":"Baixo","vocab.fan_auto":"Ventilador: Auto","vocab.fan_high":"Ventilador: Alto","vocab.fan_low":"Ventilador: Baixo","vocab.fan_medium":"Ventilador: Médio","vocab.fast_forward":"Avanço rápido","vocab.guide":"Guia","vocab.left":"Esquerda","vocab.menu":"Menu","vocab.mode_auto":"Modo: Auto","vocab.mode_cool":"Modo: Refrigerar","vocab.mode_dry":"Modo: Desumidificar","vocab.mode_fan":"Modo: Ventilar","vocab.mode_heat":"Modo: Aquecer","vocab.mute":"Mudo","vocab.off":"Desligado","vocab.on":"Ligado","vocab.open":"Abrir","vocab.oscillate":"Oscilar","vocab.pause":"Pausar","vocab.play":"Reproduzir","vocab.power":"Energia","vocab.power_off":"Desligar","vocab.power_on":"Ligar","vocab.power_toggle":"Alternar liga/desliga","vocab.rewind":"Retroceder","vocab.right":"Direita","vocab.select_ok":"Selecionar/OK","vocab.source_input":"Fonte/Entrada","vocab.speed_down":"Velocidade -","vocab.speed_up":"Velocidade +","vocab.stop":"Parar","vocab.swing_toggle":"Balanço das aletas","vocab.timer":"Temporizador","vocab.up":"Cima","vocab.volume_down":"Volume -","vocab.volume_up":"Volume +"},ru:{"_meta.review":"Programming-assistant draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Загрузка…","panel.load_failed":"Не удалось загрузить устройства: {message}","panel.open_menu":"Открыть меню","panel.tab.devices":"Устройства","panel.tagline.devices":"Управляйте ИК-устройствами и оборудованием, которое ими управляет.","panel.tagline.sniffer":"Захватывайте ИК-коды в реальном времени прямо из воздуха.","panel.tagline.clips":"Создавайте пульты, вставляя известные ИК-коды.","panel.tagline.plucker":"Извлекайте ИК-коды из ваших существующих передатчиков.","panel.tagline.mirror":"Наблюдайте за инфракрасными передачами Home Assistant в реальном времени.","common.confirm":"Подтвердить","common.cancel":"Отмена","common.are_you_sure":"Вы уверены?","common.remove":"Убрать","alias.placeholder":"Алиас для этого сигнала","alias.tag":"алиас","alias.clear":"Очистить алиас","alias.edit":"Нажмите, чтобы изменить алиас","alias.name":"Нажмите, чтобы назвать этот сигнал","picker.emitters_label":"ИК-передатчики","picker.add_emitter":"+ Добавить передатчик...","picker.no_emitters":"ИК-передатчики не найдены.","picker.all_emitters_selected":"Все передатчики выбраны.","picker.receivers_label":"Через приёмник(и):","picker.add_receiver":"+ Добавить приёмник...","picker.no_receivers":"ИК-приёмники не найдены.","picker.all_receivers_selected":"Все приёмники выбраны.","device_type.media_player":"Медиаплеер","device_type.ac":"Кондиционер","device_type.fan":"Вентилятор","device_type.light":"Светильник","device_type.switch":"Выключатель","device_type.screen":"Экран / Штора","device_type.other":"Другое","common.name":"Название","common.device_type":"Тип устройства","common.name_required":"Название обязательно.","common.creating":"Создание...","common.device_name_placeholder":"напр. Телевизор в гостиной","promote.heading":"Повысить до устройства","promote.device_name":"Название устройства","promote.device_name_required":"Название устройства обязательно.","promote.emitter_required":"Выберите хотя бы один ИК-передатчик.","promote.create_device":"Создать устройство","adddev.heading":"Добавить устройство","adddev.emitter_required":"Выберите хотя бы один ИК-передатчик.","adddev.create":"Создать","dup.heading":"Дублировать устройство","dup.hint_duplicating":"Дублирование {name}.","dup.hint_body":"Новое устройство получает копию каждой команды, привязки действия и назначения передатчика. Всё можно изменить позже.","dup.duplicating":"Дублирование...","dup.duplicate":"Дублировать","promote.description":"Создайте новое устройство HAIR. Затем вы сможете назначить ему захваченные сигналы как команды.","capture.listening":"Ожидание ИК-сигнала…","capture.instruction":'Направьте пульт на ИК-приёмник и нажмите кнопку "{name}".',"capture.remaining":"Осталось {seconds}с","capture.captured":"Сигнал захвачен!","capture.protocol":"Протокол: {protocol}","capture.protocol_raw":"Сырой","capture.verify":"Сработало? Нажмите Тест для проверки.","capture.test":"▶ Тест","capture.recapture":"↻ Захватить заново","capture.save_next":"Сохранить и учить следующий ▶▶","capture.no_signal":"⚠ Сигнал не обнаружен","capture.tip_point":"Направьте пульт прямо на ИК-приёмник","capture.tip_closer":"Подойдите ближе (в пределах 1 метра)","capture.tip_hold":"Кратко удерживайте кнопку","capture.try_again":"↻ Попробовать снова","capture.duplicate":"⚠ Обнаружен дубликат сигнала","capture.duplicate_instruction":'Этот сигнал совпадает с вашей командой "{name}". Некоторые пульты используют один сигнал для нескольких кнопок.',"capture.recapture_different":"Захватить другой","capture.save_anyway":"Всё равно сохранить","capture.error":"⚠ Ошибка захвата","capture.learning":'Обучение: "{name}"',"test_emitter.heading":"Отправить с","test_emitter.sending":"Отправка...","test_emitter.send":"Отправить","createremote.heading":"Создать пульт","createremote.type":"Тип","createremote.blank":"Пустой пульт","createremote.from_library":"Из библиотеки кодов","createremote.model":"Модель","createremote.select_model":"Выберите модель","popover.assigned_to":"Назначено","popover.new_assignment":"+ новое назначение","popover.open_in_devices":"Открыть {name} в Устройствах","popover.triggers":"Триггеры","popover.new_trigger":"+ новый триггер","popover.any_receiver":"Любой приёмник","popover.n_more":"{name} + ещё {count}","cmdrow.rename":"Нажмите, чтобы переименовать","cmdrow.tx_raw_on":"Воспроизводит захваченный Pronto. Нажмите, чтобы вместо этого передавать чистые декодированные тайминги пакета.","cmdrow.tx_raw_off":"Передаёт чистые декодированные тайминги пакета. Нажмите, чтобы вместо этого воспроизводить захваченный Pronto.","cmdrow.sends_times":"Отправляет эту команду {count} раз","cmdrow.dittos":"Добавляет {count} повторов ditto NEC","cmdrow.raw_timings":"RAW: {count} таймингов","cmdrow.not_learned":"Ещё не обучено","cmdrow.edit_code":"Посмотреть или изменить код","cmdrow.map_action":"Назначить привязку действия","cmdrow.actions":"ДЕЙСТВИЯ","cmdrow.test":"Тест","cmdrow.trigger":"Триггер","cmdrow.edit_trigger":"Изменить триггер","cmdrow.create_trigger":"Создать триггер","cmdrow.delete":"Удалить","cmdrow.learn":"Обучить","trigger.alias_tag":"алиас","trigger.event":"Событие триггера","trigger.edit_heading":"Изменить триггер","trigger.create_heading":"Создать триггер","trigger.mirror_hint":"Срабатывает, когда этот сигнал приходит извне Home Assistant (физический пульт или другое приложение), и никогда при отправках самого дома.","trigger.name_label":"Название триггера","trigger.name_placeholder":"напр. Питание ТВ","trigger.min_hits":"Мин. нажатий","trigger.min_hits_hint":"Число нажатий за 5с для срабатывания","trigger.scope_hint":"Срабатывает один раз на нажатие, сколько бы приёмников в области ни наблюдали сигнал.","trigger.save_failed":"Не удалось сохранить","common.saving":"Сохранение...","common.update":"Обновить","common.create":"Создать","common.delete":"Удалить","assign.heading":"Назначить сигнал","assign.hits":"{count} приёмов","assign.mode_existing":"Существующее устройство","assign.mode_new":"Новое устройство","assign.send_times":"Число отправок","assign.send_times_hint":"Передаёт эту команду столько раз за нажатие, для устройств, которым нужен повтор. По умолчанию 1.","assign.ditto_count":"Число ditto","assign.ditto_title":"Добавляет кадры повтора после основного кадра; некоторым строгим приёмникам нужен хотя бы один, чтобы принять команду.","assign.ditto_hint":"Добавляет кадры повтора после основного кадра; некоторым строгим приёмникам нужен хотя бы один, чтобы принять команду.","assign.assigning":"Назначение...","assign.create_assign":"Создать и назначить","assign.assign":"Назначить","assign.target_device":"Целевое устройство","assign.no_devices":'Устройств пока нет. Переключитесь на "Новое устройство", чтобы создать.',"assign.select_device":"Выберите устройство...","assign.command_name":"Название команды","assign.command_placeholder":"Введите название команды","assign.select_command":"Выберите команду...","assign.custom":"Своё...","assign.command_required":"Название команды обязательно.","assign.target_required":"Выберите целевое устройство.","assign.failed_duplicate":"Не удалось назначить. Возможно, на целевом устройстве уже есть такой код.","pluckdlg.blaster_required":"Выберите передатчик, из которого извлекать.","pluckdlg.appliance_required":"Прибор обязателен.","pluckdlg.add_heading":"Добавить передатчик","pluckdlg.loading_blasters":"Загрузка передатчиков...","pluckdlg.pluck_from":"Извлечь из","pluckdlg.select_blaster":"Выберите передатчик","pluckdlg.appliance":"Прибор","pluckdlg.appliance_placeholder":"напр. свечи","pluckdlg.name_placeholder":"напр. Свечи в гостиной","pluckdlg.signal_heading":"Извлечь сигнал","pluckdlg.pluck_failed":"Не удалось извлечь.","pluckdlg.no_response":"Нет ответа от передатчика. Попробуйте ещё раз.","pluckdlg.recognized_as":"Распознан как {protocol}","pluckdlg.valid_pronto":"Корректный код Pronto","pluckdlg.command_help":"Имя, которое вы дали этому коду при обучении в приложении производителя.","pluckdlg.command_placeholder":"напр. pwr_on","pluckdlg.plucking":"Извлечение...","pluckdlg.pluck":"Извлечь","pluckdlg.captured":"Захвачено","pluckdlg.remove_capture":"Убрать этот захват","pluckdlg.alias":"Алиас","pluckdlg.no_blasters":"Совместимые передатчики не найдены. Установите поддерживаемую ИК-интеграцию (например, Tuya Local) и сначала обучите код.","editor.ditto_disabled_cmd":"Число ditto действует, когда команда передаётся как NEC. Переключите пилюлю на NEC, чтобы включить.","editor.ditto_disabled":"Число ditto действует для декодированных сигналов (сегодня NEC). Сырые коды Pronto передаются как захвачены.","editor.copied":"Скопировано","editor.press_copy":"Нажмите Cmd/Ctrl+C","editor.valid":"Корректный код Pronto","editor.not_valid":"Пока некорректен","editor.burst_pair.one":"{count} пара импульсов","editor.burst_pair.few":"{count} пары импульсов","editor.burst_pair.many":"{count} пар импульсов","editor.burst_pair.other":"{count} пары импульсов","editor.recognized_as":"Распознан как {protocol}","editor.snap_notice":"Несущая {khz} кГц, вне ИК-стандартов. Некоторые приёмники её отвергают.","editor.snapping":"Подгонка...","editor.snap_to":"Подогнать к {khz} кГц","editor.edit_command":"Изменить команду","editor.edit_signal":"Изменить сигнал","editor.create_signal":"Создать сигнал","common.save":"Сохранить","editor.trigger_note_cmd":"У этой команды есть триггер, который перенастроится автоматически.","editor.trigger_note_sig":"У этого сигнала есть триггер, который перенастроится автоматически.","editor.alias_label":"Алиас","editor.alias_optional":"Алиас (необязательно)","editor.pronto_code":"Код Pronto","editor.select_all":"Выделить всё (затем Cmd/Ctrl+C)","editor.alias_placeholder":"напр. Питание","editor.send_times_title":"Передаёт всю команду столько раз как независимые нажатия, для устройств, которым нужен повтор.","editor.ditto_title":"Добавляет кадры повтора после основного кадра. Некоторым строгим приёмникам, особенно профессиональной аудиотехнике, нужен хотя бы один.","editor.observed.one":"Замечено при захвате: {count} ditto","editor.observed.few":"Замечено при захвате: {count} ditto","editor.observed.many":"Замечено при захвате: {count} ditto","editor.observed.other":"Замечено при захвате: {count} ditto","rel.just_now":"только что","mirror.via":"через {name}","mirror.via_n":"через {count} передатчиков","mirror.not_heard":"не услышан","mirror.heard_in":"последний раз услышан в {areas}","mirror.heard_by":"последний раз услышан {names}","mirror.chip_automation":"Отправка автоматизации","mirror.chip_integration":"Отправка интеграции","mirror.chip_test":"Ручная тестовая отправка","mirror.chip_device":"Устройство HAIR","mirror.chip_send":"Отправка","mirror.unknown_title":"Отправлен неизвестный ИК-сигнал","mirror.unknown_hint":"{name} сработал, но рядом не было никого, кто расслышал бы, что он сказал. Поставьте приёмник в пределах слышимости, чтобы поймать следующую отправку.","mirror.the_blaster":"Передатчик","mirror.sent":"Отправлено!","mirror.sent_all_n":"Отправлено! ({sent}/{total})","mirror.sent_partial":"Отправлено ({sent}/{total})","mirror.failed":"Сбой","mirror.error":"Ошибка","mirror.sending":"Отправка...","mirror.test":"Тест","mirror.stat_sends":"ОТПРАВКИ","mirror.stat_not_heard":"НЕ УСЛЫШАНЫ","mirror.stat_emitters":"ПЕРЕДАТЧИКИ","mirror.stat_signals":"СИГНАЛЫ","mirror.last_send_ago":"последняя отправка {rel} назад","mirror.last_send_just":"последняя отправка только что","mirror.no_receivers":"нет приёмников","mirror.filter_all":"Все ({count})","mirror.filter_not_heard":"Не услышаны ({count})","mirror.search":"Поиск отправок...","mirror.no_match":"Ни одна отправка не подходит.","mirror.signals.one":"{count} сигнал","mirror.signals.few":"{count} сигнала","mirror.signals.many":"{count} сигналов","mirror.signals.other":"{count} сигнала","mirror.sends_times":"Отправляет этот сигнал {count} раз","mirror.assign_disabled":"Идентичность неизвестна -- в ответ ничего не услышано, назначать нечего","mirror.assigned_one":"Назначено {device} / {command}","mirror.assigned_n":"Назначено {count} командам:","mirror.assign_title":"Назначить этот сигнал устройству HAIR","mirror.test_title":"Отправить этот сигнал через передатчик для проверки","mirror.test_disabled":"Идентичность неизвестна -- нечего отправлять","mirror.trigger_disabled":"Идентичность неизвестна -- нечего привязывать","mirror.trigger_edit":"Изменить триггер(ы) этого сигнала","mirror.trigger_create":"Срабатывает, когда этот сигнал приходит извне Home Assistant","mirror.delete_title":"Очистить эту запись (вернётся при следующей отправке)","mirror.empty_title":"Пока ничего не отправлено","mirror.empty_sub":"Команды, отправленные устройствами HAIR, автоматизациями или любой интеграцией инфракрасной платформы, появятся здесь вместе с адресатом и тем, кто их услышал.","mirror.del_trigger_title":"Удалить триггер","mirror.del_trigger_msg":"Удалить этот триггер навсегда? Использующие его автоматизации перестанут срабатывать.","mirror.clear_title":"Очистить запись Mirror","mirror.clear_msg":"Убрать эту запись из Mirror? Она вернётся при следующей отправке этого сигнала.","common.delete_failed":"Не удалось удалить: {message}","device_type.other_card":"ИК-устройство","devlist.loading":"Загрузка ИК-устройств...","devlist.empty_title":"ИК-устройств пока нет","devlist.empty_sub":"Добавьте первое устройство, чтобы начать.","devlist.add_device_plus":"+ Добавить устройство","devlist.title":"Устройства HAIR","devlist.add_device":"Добавить устройство","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"Нет TX","devlist.rx_native_title":"Принимает через родную инфракрасную платформу HA","devlist.rx_bridge_active":"Старый мост всё ещё активен. Родной приёмник его заменяет -- можно убрать блок on_pronto: из конфигурации ESPHome.","devlist.rx_bridge_title":"Принимает через старый мост событий ESPHome","devlist.rx_upgrade_title":"Обновитесь до HA 2026.6+ для родной поддержки приёмников","devlist.tx_native_title":"Отправляет через родную инфракрасную платформу HA","devlist.blasters":"Передатчики (извлекаемые)","devlist.emitters":"Передатчики","devlist.receivers":"Приёмники","devlist.proxies":"Прокси","devlist.hits_badge":"{count}x приёмов","devlist.on":"ВКЛ","devlist.off":"ВЫКЛ","devlist.delete_trigger":"Удалить триггер","devlist.delete_device":"Удалить устройство","devlist.open_plucker_title":"Открыть в Plucker","devlist.open_plucker":"Открыть в Plucker","devlist.del_trigger_msg":'Убрать "{name}"? Связанная сущность события HA тоже будет удалена.',"devlist.del_device_title":"Удалить устройство","devlist.del_device_msg":'Убрать "{name}"? Команды, привязки действий и назначения передатчиков будут удалены. Триггеры не затрагиваются.',"common.close":"Закрыть","devdetail.name_updated":"Название обновлено","devdetail.type_updated":"Тип устройства обновлён","devdetail.emitters_updated":"Передатчики обновлены","devdetail.update_failed":"Не удалось обновить: {message}","devdetail.reorder_failed":"Не удалось изменить порядок: {message}","devdetail.mapped_to":"Привязано к {action}","devdetail.mapping_cleared":"Привязка очищена","devdetail.mapping_failed":"Не удалось привязать: {message}","devdetail.sent_cmd":'"{name}" отправлено',"devdetail.send_failed":"Не удалось отправить: {message}","devdetail.cmd_updated":"Команда обновлена","devdetail.cmd_updated_repointed":"Команда обновлена. Триггер {names} перенастроен.","devdetail.rename_failed":"Не удалось переименовать: {message}","devdetail.removed":'"{name}" убрано',"devdetail.saved":'"{name}" сохранено',"devdetail.type":"Тип","devdetail.commands":"Команды ({count})","devdetail.no_commands":"Команд пока нет. Добавьте одну ниже.","devdetail.drag":"Перетащите, чтобы изменить порядок","devdetail.map_action":"Привязать действие","devdetail.none_clear":"Нет (очистить)","devdetail.sniff_title":"Захватить новый сигнал в Sniffer","devdetail.sniffed":"+ Сигнал из Sniffer","devdetail.clip_title":"Вставить новый сигнал в Clips","devdetail.clipped":"+ Вставленный сигнал","devdetail.mirror_title":"Подслушать отправку в Mirror","devdetail.mirrored":"+ Сигнал из Mirror","devdetail.del_device_title":"Удалить {name}?","devdetail.del_device_msg":"Будут удалены все захваченные команды и автоматически созданная сущность. Это действие нельзя отменить.","devdetail.del_cmd_title":"Удалить команду?","devdetail.del_cmd_msg":'Убрать "{name}"? Это нельзя отменить.',"devdetail.del_trigger_msg":"Убрать этот триггер? Связанная сущность события HA тоже будет удалена.","rel.min_ago":"{count} мин назад","rel.h_ago":"{count}ч назад","rel.d_ago":"{count}д назад","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} пульт","sniffer.remotes.few":"{count} пульта","sniffer.remotes.many":"{count} пультов","sniffer.remotes.other":"{count} пульта","sniffer.scanning":"Поиск сигналов...","sniffer.empty_title":"Неизвестные сигналы не обнаружены","sniffer.empty_body":"Когда ваши устройства ESPHome примут нераспознанные ИК-сигналы, они появятся здесь автоматически.","sniffer.empty_hint":"Попробуйте нажать кнопку пульта, который ещё не настроен.","sniffer.norx_title":"ИК-приёмник не настроен","sniffer.norx_body":"У HAIR пока нет способа принимать ИК-сигналы, поэтому Sniffer ничего не может захватить.","sniffer.norx_hint":"Настройте приёмник ESPHome с инфракрасной платформой или проверьте в Настройки, затем Устройства и службы, что ваше ИК-устройство добавлено.","sniffer.show_dismissed_title":"Восстановить скрытые ранее пульты","sniffer.show_dismissed":"Показать скрытые","sniffer.hide_dismissed":"Спрятать скрытые","sniffer.clear_all_title":"Очищает весь каталог неизвестных И список скрытых. Используйте Показать скрытые перед Очистить всё, если хотите сохранить отдельные скрытые записи.","sniffer.clear_all":"Очистить всё","sniffer.del_signal_title":"Удалить сигнал","sniffer.del_signal_msg":"Удалить этот сигнал навсегда? Это нельзя отменить.","sniffer.clear_all_confirm_title":"Очистить все сигналы","sniffer.clear_all_confirm_msg":"Убрать все неизвестные сигналы и устройства? Это нельзя отменить.","sniffer.hair_device":"Устройство HAIR","sniffer.promote":"Повысить","sniffer.dismissed":"скрыт","sniffer.restore":"Восстановить","sniffer.dismiss":"Скрыть","sniffer.addr":"адрес: {address}","sniffer.signals_head":"Сигналы ({count})","sniffer.first_seen":"Впервые замечен: {time}","sniffer.restore_first":"Сначала восстановите этот пульт","sniffer.trigger_create":"Создать сущность события HA, срабатывающую на этот сигнал","common.raw":"RAW","sniffer.hit_word.one":"приём","sniffer.hit_word.few":"приёма","sniffer.hit_word.many":"приёмов","sniffer.hit_word.other":"приёма","sniffer.signal_word.one":"сигнал","sniffer.signal_word.few":"сигнала","sniffer.signal_word.many":"сигналов","sniffer.signal_word.other":"сигнала","common.loading_plain":"Загрузка...","clips.title":"HAIR Clipper","clips.add_remote":"+ Добавить пульт","clips.empty_title":"Виртуальных пультов пока нет","clips.empty_body":"Clipper позволяет собирать пульты, вставляя коды Pronto. Создайте пульт, затем добавьте сигнал для каждой кнопки.","clips.empty_hint":'Нажмите "+ Добавить пульт" выше, чтобы начать вставленный пульт.',"clips.clear_all_title":"Удаляет все вставленные пульты и их сигналы. Сигналы из Sniffer не затрагиваются.","clips.remote_fallback":"Пульт","clips.add_signal_title":"Добавить сигнал этому пульту","clips.add_signal":"+ Добавить сигнал","clips.no_signals":'Сигналов пока нет. Нажмите "+ Добавить сигнал", чтобы вставить код Pronto.',"clips.delete_remote_title":"Удалить этот пульт и все его сигналы","clips.delete_remote":"Удалить пульт","clips.test_title":"Отправить этот сигнал через передатчик","clips.clear_all_confirm_title":"Очистить все клипы","clips.clear_all_confirm_msg":"Убрать все вставленные пульты и их сигналы? Это нельзя отменить. Сигналы из Sniffer не затрагиваются.","clips.del_remote_confirm_title":"Удалить пульт","clips.del_remote_msg_n.one":'Убрать "{name}" и его {count} сигнал? Это нельзя отменить.',"clips.del_remote_msg_n.few":'Убрать "{name}" и его {count} сигнала? Это нельзя отменить.',"clips.del_remote_msg_n.many":'Убрать "{name}" и его {count} сигналов? Это нельзя отменить.',"clips.del_remote_msg_n.other":'Убрать "{name}" и его {count} сигнала? Это нельзя отменить.',"clips.del_remote_msg":'Убрать "{name}"? Это нельзя отменить.',"pluck.vendor_unavailable":"Интеграция этого передатчика сейчас недоступна. Убедитесь, что интеграция производителя загружена.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Добавить передатчик","pluck.empty_title":"Извлечённых передатчиков пока нет","pluck.empty_body":"Plucker импортирует ИК-коды из ваших существующих передатчиков, чтобы использовать их в HAIR без повторного обучения каждого.","pluck.empty_hint":'Нажмите "+ Добавить передатчик" выше, чтобы отзеркалить передатчик.',"pluck.clear_all_title":"Удаляет все извлечённые передатчики и их сигналы. Сигналы из Sniffer и Clips не затрагиваются.","pluck.blaster_fallback":"Передатчик","pluck.promote_title":"Создать устройство HAIR из этого передатчика","pluck.pluck_signal_title":"Извлечь код из этого передатчика","pluck.pluck_signal":"+ Извлечь сигнал","pluck.no_signals":'Сигналов пока нет. Нажмите "+ Извлечь сигнал", чтобы достать код из этого передатчика.',"pluck.delete_blaster_title":"Удалить этот передатчик и все его сигналы","pluck.delete_blaster":"Удалить передатчик","pluck.clear_all_confirm_title":"Очистить все извлечённые","pluck.clear_all_confirm_msg":"Убрать все извлечённые передатчики и их сигналы? Это нельзя отменить. Сигналы из Sniffer и Clips не затрагиваются.","pluck.del_blaster_confirm_title":"Удалить передатчик","devdetail.custom_action":"Своё...","devdetail.custom_action_placeholder":"напр. temp_30","devdetail.set":"Задать","vocab.back_return":"Назад","vocab.brightness_down":"Яркость -","vocab.brightness_up":"Яркость +","vocab.channel_down":"Канал -","vocab.channel_up":"Канал +","vocab.close":"Закрыть","vocab.color_temp_cooler":"Холоднее белый","vocab.color_temp_warmer":"Теплее белый","vocab.down":"Вниз","vocab.fan_auto":"Вентилятор: Авто","vocab.fan_high":"Вентилятор: Высокая","vocab.fan_low":"Вентилятор: Низкая","vocab.fan_medium":"Вентилятор: Средняя","vocab.fast_forward":"Перемотка вперёд","vocab.guide":"Телегид","vocab.left":"Влево","vocab.menu":"Меню","vocab.mode_auto":"Режим: Авто","vocab.mode_cool":"Режим: Охлаждение","vocab.mode_dry":"Режим: Осушение","vocab.mode_fan":"Режим: Вентиляция","vocab.mode_heat":"Режим: Обогрев","vocab.mute":"Без звука","vocab.off":"Выключено","vocab.on":"Включено","vocab.open":"Открыть","vocab.oscillate":"Вращение","vocab.pause":"Пауза","vocab.play":"Воспроизведение","vocab.power":"Питание","vocab.power_off":"Выключить","vocab.power_on":"Включить","vocab.power_toggle":"Переключить питание","vocab.rewind":"Перемотка назад","vocab.right":"Вправо","vocab.select_ok":"Выбор/OK","vocab.source_input":"Источник/Вход","vocab.speed_down":"Скорость -","vocab.speed_up":"Скорость +","vocab.stop":"Стоп","vocab.swing_toggle":"Качание жалюзи","vocab.timer":"Таймер","vocab.up":"Вверх","vocab.volume_down":"Громкость -","vocab.volume_up":"Громкость +"}};let be="en",fe="en",ye=new Intl.PluralRules("en");function we(){return fe}function ke(e,t){const i=ve[be];let a=i?.[e]??_e[e]??e;if(t)for(const[e,i]of Object.entries(t))a=a.split(`{${e}}`).join(String(i));return a}function xe(e){const t=`vocab.${function(e){return e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/_+/g,"_").replace(/^_+|_+$/g,"")}(e)}`,i=ve[be];return i?.[t]??_e[t]??e}function $e(e,t,i){const a=ye.select(t),r=ve[be],o=`${e}.${a}`,n=`${e}.other`;let s=r?.[o]??r?.[n]??_e[o]??_e[n]??e;if(s=s.split("{count}").join(String(t)),i)for(const[e,t]of Object.entries(i))s=s.split(`{${e}}`).join(String(t));return s}const Se=e=>(...t)=>({_$litDirective$:e,values:t});let Ce=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,i){this._$Ct=e,this._$AM=t,this._$Ci=i}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};const{I:Ae}=re,ze=e=>e,De=()=>document.createComment(""),Ee=(e,t,i)=>{const a=e._$AA.parentNode,r=void 0===t?e._$AB:t._$AA;if(void 0===i){const t=a.insertBefore(De(),r),o=a.insertBefore(De(),r);i=new Ae(t,o,e,e.options)}else{const t=i._$AB.nextSibling,o=i._$AM,n=o!==e;if(n){let t;i._$AQ?.(e),i._$AM=e,void 0!==i._$AP&&(t=e._$AU)!==o._$AU&&i._$AP(t)}if(t!==r||n){let e=i._$AA;for(;e!==t;){const t=ze(e).nextSibling;ze(a).insertBefore(e,r),e=t}}}return i},Ie=(e,t,i=e)=>(e._$AI(t,i),e),Te={},Re=(e,t=Te)=>e._$AH=t,Pe=e=>{e._$AR(),e._$AA.remove()},He=Se(class extends Ce{constructor(){super(...arguments),this.key=F}render(e,t){return this.key=e,t}update(e,[t,i]){return t!==this.key&&(Re(e),this.key=t),i}}),Ne=(e,t,i)=>{const a=new Map;for(let r=t;r<=i;r++)a.set(e[r],r);return a},Me=Se(class extends Ce{constructor(e){if(super(e),2!==e.type)throw Error("repeat() can only be used in text expressions")}dt(e,t,i){let a;void 0===i?i=t:void 0!==t&&(a=t);const r=[],o=[];let n=0;for(const t of e)r[n]=a?a(t,n):n,o[n]=i(t,n),n++;return{values:o,keys:r}}render(e,t,i){return this.dt(e,t,i).values}update(e,[t,i,a]){const r=(e=>e._$AH)(e),{values:o,keys:n}=this.dt(t,i,a);if(!Array.isArray(r))return this.ut=n,o;const s=this.ut??=[],l=[];let d,c,p=0,g=r.length-1,m=0,u=o.length-1;for(;p<=g&&m<=u;)if(null===r[p])p++;else if(null===r[g])g--;else if(s[p]===n[m])l[m]=Ie(r[p],o[m]),p++,m++;else if(s[g]===n[u])l[u]=Ie(r[g],o[u]),g--,u--;else if(s[p]===n[u])l[u]=Ie(r[p],o[u]),Ee(e,l[u+1],r[p]),p++,u--;else if(s[g]===n[m])l[m]=Ie(r[g],o[m]),Ee(e,r[p],r[g]),g--,m++;else if(void 0===d&&(d=Ne(n,m,u),c=Ne(s,p,g)),d.has(s[p]))if(d.has(s[g])){const t=c.get(n[m]),i=void 0!==t?r[t]:null;if(null===i){const t=Ee(e,r[p]);Ie(t,o[m]),l[m]=t}else l[m]=Ie(i,o[m]),Ee(e,r[p],i),r[t]=null;m++}else Pe(r[g]),g--;else Pe(r[p]),p++;for(;m<=u;){const t=Ee(e,l[u+1]);Ie(t,o[m]),l[m++]=t}for(;p<=g;){const e=r[p++];null!==e&&Pe(e)}return this.ut=n,Re(e,l),U}});function je(e,t,i){return(t=function(e){var t=function(e,t){if("object"!=typeof e||!e)return e;var i=e[Symbol.toPrimitive];if(void 0!==i){var a=i.call(e,t);if("object"!=typeof a)return a;throw new TypeError("@@toPrimitive must return a primitive value.")}return String(e)}(e,"string");return"symbol"==typeof t?t:t+""}(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function Le(){return Le=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var i=arguments[t];for(var a in i)({}).hasOwnProperty.call(i,a)&&(e[a]=i[a])}return e},Le.apply(null,arguments)}function Ve(e,t){var i=Object.keys(e);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);t&&(a=a.filter(function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable})),i.push.apply(i,a)}return i}function qe(e){for(var t=1;t<arguments.length;t++){var i=null!=arguments[t]?arguments[t]:{};t%2?Ve(Object(i),!0).forEach(function(t){je(e,t,i[t])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(i)):Ve(Object(i)).forEach(function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(i,t))})}return e}function Oe(e){return Oe="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},Oe(e)}function Be(e){if("undefined"!=typeof window&&window.navigator)return!!navigator.userAgent.match(e)}var Ue=Be(/(?:Trident.*rv[ :]?11\.|msie|iemobile|Windows Phone)/i),Fe=Be(/Edge/i),We=Be(/firefox/i),Ge=Be(/safari/i)&&!Be(/chrome/i)&&!Be(/android/i),Ze=Be(/iP(ad|od|hone)/i),Ke=Be(/chrome/i)&&Be(/android/i),Xe={capture:!1,passive:!1};function Ye(e,t,i){e.addEventListener(t,i,!Ue&&Xe)}function Qe(e,t,i){e.removeEventListener(t,i,!Ue&&Xe)}function Je(e,t){if(t){if(">"===t[0]&&(t=t.substring(1)),e)try{if(e.matches)return e.matches(t);if(e.msMatchesSelector)return e.msMatchesSelector(t);if(e.webkitMatchesSelector)return e.webkitMatchesSelector(t)}catch(e){return!1}return!1}}function et(e){return e.host&&e!==document&&e.host.nodeType&&e.host!==e?e.host:e.parentNode}function tt(e,t,i,a){if(e){i=i||document;do{if(null!=t&&(">"===t[0]?e.parentNode===i&&Je(e,t):Je(e,t))||a&&e===i)return e;if(e===i)break}while(e=et(e))}return null}var it,at=/\s+/g;function rt(e,t,i){if(e&&t)if(e.classList)e.classList[i?"add":"remove"](t);else{var a=(" "+e.className+" ").replace(at," ").replace(" "+t+" "," ");e.className=(a+(i?" "+t:"")).replace(at," ")}}function ot(e,t,i){var a=e&&e.style;if(a){if(void 0===i)return document.defaultView&&document.defaultView.getComputedStyle?i=document.defaultView.getComputedStyle(e,""):e.currentStyle&&(i=e.currentStyle),void 0===t?i:i[t];t in a||-1!==t.indexOf("webkit")||(t="-webkit-"+t),a[t]=i+("string"==typeof i?"":"px")}}function nt(e,t){var i="";if("string"==typeof e)i=e;else do{var a=ot(e,"transform");a&&"none"!==a&&(i=a+" "+i)}while(!t&&(e=e.parentNode));var r=window.DOMMatrix||window.WebKitCSSMatrix||window.CSSMatrix||window.MSCSSMatrix;return r&&new r(i)}function st(e,t,i){if(e){var a=e.getElementsByTagName(t),r=0,o=a.length;if(i)for(;r<o;r++)i(a[r],r);return a}return[]}function lt(){return document.scrollingElement||document.documentElement}function dt(e,t,i,a,r){if(e.getBoundingClientRect||e===window){var o,n,s,l,d,c,p;if(e!==window&&e.parentNode&&e!==lt()?(n=(o=e.getBoundingClientRect()).top,s=o.left,l=o.bottom,d=o.right,c=o.height,p=o.width):(n=0,s=0,l=window.innerHeight,d=window.innerWidth,c=window.innerHeight,p=window.innerWidth),(t||i)&&e!==window&&(r=r||e.parentNode,!Ue))do{if(r&&r.getBoundingClientRect&&("none"!==ot(r,"transform")||i&&"static"!==ot(r,"position"))){var g=r.getBoundingClientRect();n-=g.top+parseInt(ot(r,"border-top-width")),s-=g.left+parseInt(ot(r,"border-left-width")),l=n+o.height,d=s+o.width;break}}while(r=r.parentNode);if(a&&e!==window){var m=nt(r||e),u=m&&m.a,h=m&&m.d;m&&(l=(n/=h)+(c/=h),d=(s/=u)+(p/=u))}return{top:n,left:s,bottom:l,right:d,width:p,height:c}}}function ct(e,t,i){for(var a=ht(e,!0),r=dt(e)[t];a;){if(!(r>=dt(a)[i]))return a;if(a===lt())break;a=ht(a,!1)}return!1}function pt(e,t,i,a){for(var r=0,o=0,n=e.children;o<n.length;){if("none"!==n[o].style.display&&n[o]!==bi.ghost&&(a||n[o]!==bi.dragged)&&tt(n[o],i.draggable,e,!1)){if(r===t)return n[o];r++}o++}return null}function gt(e,t){for(var i=e.lastElementChild;i&&(i===bi.ghost||"none"===ot(i,"display")||t&&!Je(i,t));)i=i.previousElementSibling;return i||null}function mt(e,t){var i=0;if(!e||!e.parentNode)return-1;for(;e=e.previousElementSibling;)"TEMPLATE"===e.nodeName.toUpperCase()||e===bi.clone||t&&!Je(e,t)||i++;return i}function ut(e){var t=0,i=0,a=lt();if(e)do{var r=nt(e),o=r.a,n=r.d;t+=e.scrollLeft*o,i+=e.scrollTop*n}while(e!==a&&(e=e.parentNode));return[t,i]}function ht(e,t){if(!e||!e.getBoundingClientRect)return lt();var i=e,a=!1;do{if(i.clientWidth<i.scrollWidth||i.clientHeight<i.scrollHeight){var r=ot(i);if(i.clientWidth<i.scrollWidth&&("auto"==r.overflowX||"scroll"==r.overflowX)||i.clientHeight<i.scrollHeight&&("auto"==r.overflowY||"scroll"==r.overflowY)){if(!i.getBoundingClientRect||i===document.body)return lt();if(a||t)return i;a=!0}}}while(i=i.parentNode);return lt()}function _t(e,t){return Math.round(e.top)===Math.round(t.top)&&Math.round(e.left)===Math.round(t.left)&&Math.round(e.height)===Math.round(t.height)&&Math.round(e.width)===Math.round(t.width)}function vt(e,t){return function(){if(!it){var i=arguments;1===i.length?e.call(this,i[0]):e.apply(this,i),it=setTimeout(function(){it=void 0},t)}}}function bt(e,t,i){e.scrollLeft+=t,e.scrollTop+=i}function ft(e){var t=window.Polymer,i=window.jQuery||window.Zepto;return t&&t.dom?t.dom(e).cloneNode(!0):i?i(e).clone(!0)[0]:e.cloneNode(!0)}function yt(e,t,i){var a={};return Array.from(e.children).forEach(function(r){var o,n,s,l;if(tt(r,t.draggable,e,!1)&&!r.animated&&r!==i){var d=dt(r);a.left=Math.min(null!==(o=a.left)&&void 0!==o?o:1/0,d.left),a.top=Math.min(null!==(n=a.top)&&void 0!==n?n:1/0,d.top),a.right=Math.max(null!==(s=a.right)&&void 0!==s?s:-1/0,d.right),a.bottom=Math.max(null!==(l=a.bottom)&&void 0!==l?l:-1/0,d.bottom)}}),a.width=a.right-a.left,a.height=a.bottom-a.top,a.x=a.left,a.y=a.top,a}var wt="Sortable"+(new Date).getTime();var kt=[],xt={initializeByDefault:!0},$t={mount:function(e){for(var t in xt)xt.hasOwnProperty(t)&&!(t in e)&&(e[t]=xt[t]);kt.forEach(function(t){if(t.pluginName===e.pluginName)throw"Sortable: Cannot mount plugin ".concat(e.pluginName," more than once")}),kt.push(e)},pluginEvent:function(e,t,i){var a=this;this.eventCanceled=!1,i.cancel=function(){a.eventCanceled=!0};var r=e+"Global";kt.forEach(function(a){t[a.pluginName]&&(t[a.pluginName][r]&&t[a.pluginName][r](qe({sortable:t},i)),t.options[a.pluginName]&&t[a.pluginName][e]&&t[a.pluginName][e](qe({sortable:t},i)))})},initializePlugins:function(e,t,i,a){for(var r in kt.forEach(function(a){var r=a.pluginName;if(e.options[r]||a.initializeByDefault){var o=new a(e,t,e.options);o.sortable=e,o.options=e.options,e[r]=o,Le(i,o.defaults)}}),e.options)if(e.options.hasOwnProperty(r)){var o=this.modifyOption(e,r,e.options[r]);void 0!==o&&(e.options[r]=o)}},getEventProperties:function(e,t){var i={};return kt.forEach(function(a){"function"==typeof a.eventProperties&&Le(i,a.eventProperties.call(t[a.pluginName],e))}),i},modifyOption:function(e,t,i){var a;return kt.forEach(function(r){e[r.pluginName]&&r.optionListeners&&"function"==typeof r.optionListeners[t]&&(a=r.optionListeners[t].call(e[r.pluginName],i))}),a}},St=["evt"],Ct=function(e,t){var i=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},a=i.evt,r=function(e,t){if(null==e)return{};var i,a,r=function(e,t){if(null==e)return{};var i={};for(var a in e)if({}.hasOwnProperty.call(e,a)){if(-1!==t.indexOf(a))continue;i[a]=e[a]}return i}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(a=0;a<o.length;a++)i=o[a],-1===t.indexOf(i)&&{}.propertyIsEnumerable.call(e,i)&&(r[i]=e[i])}return r}(i,St);$t.pluginEvent.bind(bi)(e,t,qe({dragEl:zt,parentEl:Dt,ghostEl:Et,rootEl:It,nextEl:Tt,lastDownEl:Rt,cloneEl:Pt,cloneHidden:Ht,dragStarted:Zt,putSortable:qt,activeSortable:bi.active,originalEvent:a,oldIndex:Nt,oldDraggableIndex:jt,newIndex:Mt,newDraggableIndex:Lt,hideGhostForTarget:ui,unhideGhostForTarget:hi,cloneNowHidden:function(){Ht=!0},cloneNowShown:function(){Ht=!1},dispatchSortableEvent:function(e){At({sortable:t,name:e,originalEvent:a})}},r))};function At(e){!function(e){var t=e.sortable,i=e.rootEl,a=e.name,r=e.targetEl,o=e.cloneEl,n=e.toEl,s=e.fromEl,l=e.oldIndex,d=e.newIndex,c=e.oldDraggableIndex,p=e.newDraggableIndex,g=e.originalEvent,m=e.putSortable,u=e.extraEventProperties;if(t=t||i&&i[wt]){var h,_=t.options,v="on"+a.charAt(0).toUpperCase()+a.substr(1);!window.CustomEvent||Ue||Fe?(h=document.createEvent("Event")).initEvent(a,!0,!0):h=new CustomEvent(a,{bubbles:!0,cancelable:!0}),h.to=n||i,h.from=s||i,h.item=r||i,h.clone=o,h.oldIndex=l,h.newIndex=d,h.oldDraggableIndex=c,h.newDraggableIndex=p,h.originalEvent=g,h.pullMode=m?m.lastPutMode:void 0;var b=qe(qe({},u),$t.getEventProperties(a,t));for(var f in b)h[f]=b[f];i&&i.dispatchEvent(h),_[v]&&_[v].call(t,h)}}(qe({putSortable:qt,cloneEl:Pt,targetEl:zt,rootEl:It,oldIndex:Nt,oldDraggableIndex:jt,newIndex:Mt,newDraggableIndex:Lt},e))}var zt,Dt,Et,It,Tt,Rt,Pt,Ht,Nt,Mt,jt,Lt,Vt,qt,Ot,Bt,Ut,Ft,Wt,Gt,Zt,Kt,Xt,Yt,Qt,Jt=!1,ei=!1,ti=[],ii=!1,ai=!1,ri=[],oi=!1,ni=[],si="undefined"!=typeof document,li=Ze,di=Fe||Ue?"cssFloat":"float",ci=si&&!Ke&&!Ze&&"draggable"in document.createElement("div"),pi=function(){if(si){if(Ue)return!1;var e=document.createElement("x");return e.style.cssText="pointer-events:auto","auto"===e.style.pointerEvents}}(),gi=function(e,t){var i=ot(e),a=parseInt(i.width)-parseInt(i.paddingLeft)-parseInt(i.paddingRight)-parseInt(i.borderLeftWidth)-parseInt(i.borderRightWidth),r=pt(e,0,t),o=pt(e,1,t),n=r&&ot(r),s=o&&ot(o),l=n&&parseInt(n.marginLeft)+parseInt(n.marginRight)+dt(r).width,d=s&&parseInt(s.marginLeft)+parseInt(s.marginRight)+dt(o).width;if("flex"===i.display)return"column"===i.flexDirection||"column-reverse"===i.flexDirection?"vertical":"horizontal";if("grid"===i.display)return i.gridTemplateColumns.split(" ").length<=1?"vertical":"horizontal";if(r&&n.float&&"none"!==n.float){var c="left"===n.float?"left":"right";return!o||"both"!==s.clear&&s.clear!==c?"horizontal":"vertical"}return r&&("block"===n.display||"flex"===n.display||"table"===n.display||"grid"===n.display||l>=a&&"none"===i[di]||o&&"none"===i[di]&&l+d>a)?"vertical":"horizontal"},mi=function(e){function t(e,i){return function(a,r,o,n){var s=a.options.group.name&&r.options.group.name&&a.options.group.name===r.options.group.name;if(null==e&&(i||s))return!0;if(null==e||!1===e)return!1;if(i&&"clone"===e)return e;if("function"==typeof e)return t(e(a,r,o,n),i)(a,r,o,n);var l=(i?a:r).options.group.name;return!0===e||"string"==typeof e&&e===l||e.join&&e.indexOf(l)>-1}}var i={},a=e.group;a&&"object"==Oe(a)||(a={name:a}),i.name=a.name,i.checkPull=t(a.pull,!0),i.checkPut=t(a.put),i.revertClone=a.revertClone,e.group=i},ui=function(){!pi&&Et&&ot(Et,"display","none")},hi=function(){!pi&&Et&&ot(Et,"display","")};si&&!Ke&&document.addEventListener("click",function(e){if(ei)return e.preventDefault(),e.stopPropagation&&e.stopPropagation(),e.stopImmediatePropagation&&e.stopImmediatePropagation(),ei=!1,!1},!0);var _i=function(e){if(zt){var t=function(e,t){var i;return ti.some(function(a){var r=a[wt].options.emptyInsertThreshold;if(r&&!gt(a)){var o=dt(a),n=e>=o.left-r&&e<=o.right+r,s=t>=o.top-r&&t<=o.bottom+r;return n&&s?i=a:void 0}}),i}((e=e.touches?e.touches[0]:e).clientX,e.clientY);if(t){var i={};for(var a in e)e.hasOwnProperty(a)&&(i[a]=e[a]);i.target=i.rootEl=t,i.preventDefault=void 0,i.stopPropagation=void 0,t[wt]._onDragOver(i)}}},vi=function(e){zt&&zt.parentNode[wt]._isOutsideThisEl(e.target)};function bi(e,t){if(!e||!e.nodeType||1!==e.nodeType)throw"Sortable: `el` must be an HTMLElement, not ".concat({}.toString.call(e));this.el=e,this.options=t=Le({},t),e[wt]=this;var i,a,r={group:null,sort:!0,disabled:!1,store:null,handle:null,draggable:/^[uo]l$/i.test(e.nodeName)?">li":">*",swapThreshold:1,invertSwap:!1,invertedSwapThreshold:null,removeCloneOnHide:!0,direction:function(){return gi(e,this.options)},ghostClass:"sortable-ghost",chosenClass:"sortable-chosen",dragClass:"sortable-drag",ignore:"a, img",filter:null,preventOnFilter:!0,animation:0,easing:null,setData:function(e,t){e.setData("Text",t.textContent)},dropBubble:!1,dragoverBubble:!1,dataIdAttr:"data-id",delay:0,delayOnTouchOnly:!1,touchStartThreshold:(Number.parseInt?Number:window).parseInt(window.devicePixelRatio,10)||1,forceFallback:!1,fallbackClass:"sortable-fallback",fallbackOnBody:!1,fallbackTolerance:0,fallbackOffset:{x:0,y:0},supportPointer:!1!==bi.supportPointer&&"PointerEvent"in window&&(!Ge||Ze),emptyInsertThreshold:5};for(var o in $t.initializePlugins(this,e,r),r)!(o in t)&&(t[o]=r[o]);for(var n in mi(t),this)"_"===n.charAt(0)&&"function"==typeof this[n]&&(this[n]=this[n].bind(this));this.nativeDraggable=!t.forceFallback&&ci,this.nativeDraggable&&(this.options.touchStartThreshold=1),t.supportPointer?Ye(e,"pointerdown",this._onTapStart):(Ye(e,"mousedown",this._onTapStart),Ye(e,"touchstart",this._onTapStart)),this.nativeDraggable&&(Ye(e,"dragover",this),Ye(e,"dragenter",this)),ti.push(this.el),t.store&&t.store.get&&this.sort(t.store.get(this)||[]),Le(this,(a=[],{captureAnimationState:function(){a=[],this.options.animation&&[].slice.call(this.el.children).forEach(function(e){if("none"!==ot(e,"display")&&e!==bi.ghost){a.push({target:e,rect:dt(e)});var t=qe({},a[a.length-1].rect);if(e.thisAnimationDuration){var i=nt(e,!0);i&&(t.top-=i.f,t.left-=i.e)}e.fromRect=t}})},addAnimationState:function(e){a.push(e)},removeAnimationState:function(e){a.splice(function(e,t){for(var i in e)if(e.hasOwnProperty(i))for(var a in t)if(t.hasOwnProperty(a)&&t[a]===e[i][a])return Number(i);return-1}(a,{target:e}),1)},animateAll:function(e){var t=this;if(!this.options.animation)return clearTimeout(i),void("function"==typeof e&&e());var r=!1,o=0;a.forEach(function(e){var i=0,a=e.target,n=a.fromRect,s=dt(a),l=a.prevFromRect,d=a.prevToRect,c=e.rect,p=nt(a,!0);p&&(s.top-=p.f,s.left-=p.e),a.toRect=s,a.thisAnimationDuration&&_t(l,s)&&!_t(n,s)&&(c.top-s.top)/(c.left-s.left)===(n.top-s.top)/(n.left-s.left)&&(i=function(e,t,i,a){return Math.sqrt(Math.pow(t.top-e.top,2)+Math.pow(t.left-e.left,2))/Math.sqrt(Math.pow(t.top-i.top,2)+Math.pow(t.left-i.left,2))*a.animation}(c,l,d,t.options)),_t(s,n)||(a.prevFromRect=n,a.prevToRect=s,i||(i=t.options.animation),t.animate(a,c,s,i)),i&&(r=!0,o=Math.max(o,i),clearTimeout(a.animationResetTimer),a.animationResetTimer=setTimeout(function(){a.animationTime=0,a.prevFromRect=null,a.fromRect=null,a.prevToRect=null,a.thisAnimationDuration=null},i),a.thisAnimationDuration=i)}),clearTimeout(i),r?i=setTimeout(function(){"function"==typeof e&&e()},o):"function"==typeof e&&e(),a=[]},animate:function(e,t,i,a){if(a){ot(e,"transition",""),ot(e,"transform","");var r=nt(this.el),o=r&&r.a,n=r&&r.d,s=(t.left-i.left)/(o||1),l=(t.top-i.top)/(n||1);e.animatingX=!!s,e.animatingY=!!l,ot(e,"transform","translate3d("+s+"px,"+l+"px,0)"),this.forRepaintDummy=function(e){return e.offsetWidth}(e),ot(e,"transition","transform "+a+"ms"+(this.options.easing?" "+this.options.easing:"")),ot(e,"transform","translate3d(0,0,0)"),"number"==typeof e.animated&&clearTimeout(e.animated),e.animated=setTimeout(function(){ot(e,"transition",""),ot(e,"transform",""),e.animated=!1,e.animatingX=!1,e.animatingY=!1},a)}}}))}function fi(e,t,i,a,r,o,n,s){var l,d,c=e[wt],p=c.options.onMove;return!window.CustomEvent||Ue||Fe?(l=document.createEvent("Event")).initEvent("move",!0,!0):l=new CustomEvent("move",{bubbles:!0,cancelable:!0}),l.to=t,l.from=e,l.dragged=i,l.draggedRect=a,l.related=r||t,l.relatedRect=o||dt(t),l.willInsertAfter=s,l.originalEvent=n,e.dispatchEvent(l),p&&(d=p.call(c,l,n)),d}function yi(e){e.draggable=!1}function wi(){oi=!1}function ki(e){for(var t=e.tagName+e.className+e.src+e.href+e.textContent,i=t.length,a=0;i--;)a+=t.charCodeAt(i);return a.toString(36)}function xi(e){return setTimeout(e,0)}function $i(e){return clearTimeout(e)}bi.prototype={constructor:bi,_isOutsideThisEl:function(e){this.el.contains(e)||e===this.el||(Kt=null)},_getDirection:function(e,t){return"function"==typeof this.options.direction?this.options.direction.call(this,e,t,zt):this.options.direction},_onTapStart:function(e){if(e.cancelable){var t=this,i=this.el,a=this.options,r=a.preventOnFilter,o=e.type,n=e.touches&&e.touches[0]||e.pointerType&&"touch"===e.pointerType&&e,s=(n||e).target,l=e.target.shadowRoot&&(e.path&&e.path[0]||e.composedPath&&e.composedPath()[0])||s,d=a.filter;if(function(e){ni.length=0;for(var t=e.getElementsByTagName("input"),i=t.length;i--;){var a=t[i];a.checked&&ni.push(a)}}(i),!zt&&!(/mousedown|pointerdown/.test(o)&&0!==e.button||a.disabled)&&!l.isContentEditable&&(this.nativeDraggable||!Ge||!s||"SELECT"!==s.tagName.toUpperCase())&&!((s=tt(s,a.draggable,i,!1))&&s.animated||Rt===s)){if(Nt=mt(s),jt=mt(s,a.draggable),"function"==typeof d){if(d.call(this,e,s,this))return At({sortable:t,rootEl:l,name:"filter",targetEl:s,toEl:i,fromEl:i}),Ct("filter",t,{evt:e}),void(r&&e.preventDefault())}else if(d&&(d=d.split(",").some(function(a){if(a=tt(l,a.trim(),i,!1))return At({sortable:t,rootEl:a,name:"filter",targetEl:s,fromEl:i,toEl:i}),Ct("filter",t,{evt:e}),!0})))return void(r&&e.preventDefault());a.handle&&!tt(l,a.handle,i,!1)||this._prepareDragStart(e,n,s)}}},_prepareDragStart:function(e,t,i){var a,r=this,o=r.el,n=r.options,s=o.ownerDocument;if(i&&!zt&&i.parentNode===o){var l=dt(i);if(It=o,Dt=(zt=i).parentNode,Tt=zt.nextSibling,Rt=i,Vt=n.group,bi.dragged=zt,Ot={target:zt,clientX:(t||e).clientX,clientY:(t||e).clientY},Wt=Ot.clientX-l.left,Gt=Ot.clientY-l.top,this._lastX=(t||e).clientX,this._lastY=(t||e).clientY,zt.style["will-change"]="all",a=function(){Ct("delayEnded",r,{evt:e}),bi.eventCanceled?r._onDrop():(r._disableDelayedDragEvents(),!We&&r.nativeDraggable&&(zt.draggable=!0),r._triggerDragStart(e,t),At({sortable:r,name:"choose",originalEvent:e}),rt(zt,n.chosenClass,!0))},n.ignore.split(",").forEach(function(e){st(zt,e.trim(),yi)}),Ye(s,"dragover",_i),Ye(s,"mousemove",_i),Ye(s,"touchmove",_i),n.supportPointer?(Ye(s,"pointerup",r._onDrop),!this.nativeDraggable&&Ye(s,"pointercancel",r._onDrop)):(Ye(s,"mouseup",r._onDrop),Ye(s,"touchend",r._onDrop),Ye(s,"touchcancel",r._onDrop)),We&&this.nativeDraggable&&(this.options.touchStartThreshold=4,zt.draggable=!0),Ct("delayStart",this,{evt:e}),!n.delay||n.delayOnTouchOnly&&!t||this.nativeDraggable&&(Fe||Ue))a();else{if(bi.eventCanceled)return void this._onDrop();n.supportPointer?(Ye(s,"pointerup",r._disableDelayedDrag),Ye(s,"pointercancel",r._disableDelayedDrag)):(Ye(s,"mouseup",r._disableDelayedDrag),Ye(s,"touchend",r._disableDelayedDrag),Ye(s,"touchcancel",r._disableDelayedDrag)),Ye(s,"mousemove",r._delayedDragTouchMoveHandler),Ye(s,"touchmove",r._delayedDragTouchMoveHandler),n.supportPointer&&Ye(s,"pointermove",r._delayedDragTouchMoveHandler),r._dragStartTimer=setTimeout(a,n.delay)}}},_delayedDragTouchMoveHandler:function(e){var t=e.touches?e.touches[0]:e;Math.max(Math.abs(t.clientX-this._lastX),Math.abs(t.clientY-this._lastY))>=Math.floor(this.options.touchStartThreshold/(this.nativeDraggable&&window.devicePixelRatio||1))&&this._disableDelayedDrag()},_disableDelayedDrag:function(){zt&&yi(zt),clearTimeout(this._dragStartTimer),this._disableDelayedDragEvents()},_disableDelayedDragEvents:function(){var e=this.el.ownerDocument;Qe(e,"mouseup",this._disableDelayedDrag),Qe(e,"touchend",this._disableDelayedDrag),Qe(e,"touchcancel",this._disableDelayedDrag),Qe(e,"pointerup",this._disableDelayedDrag),Qe(e,"pointercancel",this._disableDelayedDrag),Qe(e,"mousemove",this._delayedDragTouchMoveHandler),Qe(e,"touchmove",this._delayedDragTouchMoveHandler),Qe(e,"pointermove",this._delayedDragTouchMoveHandler)},_triggerDragStart:function(e,t){t=t||"touch"==e.pointerType&&e,!this.nativeDraggable||t?this.options.supportPointer?Ye(document,"pointermove",this._onTouchMove):Ye(document,t?"touchmove":"mousemove",this._onTouchMove):(Ye(zt,"dragend",this),Ye(It,"dragstart",this._onDragStart));try{document.selection?xi(function(){document.selection.empty()}):window.getSelection().removeAllRanges()}catch(e){}},_dragStarted:function(e,t){if(Jt=!1,It&&zt){Ct("dragStarted",this,{evt:t}),this.nativeDraggable&&Ye(document,"dragover",vi);var i=this.options;!e&&rt(zt,i.dragClass,!1),rt(zt,i.ghostClass,!0),bi.active=this,e&&this._appendGhost(),At({sortable:this,name:"start",originalEvent:t})}else this._nulling()},_emulateDragOver:function(){if(Bt){this._lastX=Bt.clientX,this._lastY=Bt.clientY,ui();for(var e=document.elementFromPoint(Bt.clientX,Bt.clientY),t=e;e&&e.shadowRoot&&(e=e.shadowRoot.elementFromPoint(Bt.clientX,Bt.clientY))!==t;)t=e;if(zt.parentNode[wt]._isOutsideThisEl(e),t)do{if(t[wt]&&t[wt]._onDragOver({clientX:Bt.clientX,clientY:Bt.clientY,target:e,rootEl:t})&&!this.options.dragoverBubble)break;e=t}while(t=et(t));hi()}},_onTouchMove:function(e){if(Ot){var t=this.options,i=t.fallbackTolerance,a=t.fallbackOffset,r=e.touches?e.touches[0]:e,o=Et&&nt(Et,!0),n=Et&&o&&o.a,s=Et&&o&&o.d,l=li&&Qt&&ut(Qt),d=(r.clientX-Ot.clientX+a.x)/(n||1)+(l?l[0]-ri[0]:0)/(n||1),c=(r.clientY-Ot.clientY+a.y)/(s||1)+(l?l[1]-ri[1]:0)/(s||1);if(!bi.active&&!Jt){if(i&&Math.max(Math.abs(r.clientX-this._lastX),Math.abs(r.clientY-this._lastY))<i)return;this._onDragStart(e,!0)}if(Et){o?(o.e+=d-(Ut||0),o.f+=c-(Ft||0)):o={a:1,b:0,c:0,d:1,e:d,f:c};var p="matrix(".concat(o.a,",").concat(o.b,",").concat(o.c,",").concat(o.d,",").concat(o.e,",").concat(o.f,")");ot(Et,"webkitTransform",p),ot(Et,"mozTransform",p),ot(Et,"msTransform",p),ot(Et,"transform",p),Ut=d,Ft=c,Bt=r}e.cancelable&&e.preventDefault()}},_appendGhost:function(){if(!Et){var e=this.options.fallbackOnBody?document.body:It,t=dt(zt,!0,li,!0,e),i=this.options;if(li){for(Qt=e;"static"===ot(Qt,"position")&&"none"===ot(Qt,"transform")&&Qt!==document;)Qt=Qt.parentNode;Qt!==document.body&&Qt!==document.documentElement?(Qt===document&&(Qt=lt()),t.top+=Qt.scrollTop,t.left+=Qt.scrollLeft):Qt=lt(),ri=ut(Qt)}rt(Et=zt.cloneNode(!0),i.ghostClass,!1),rt(Et,i.fallbackClass,!0),rt(Et,i.dragClass,!0),ot(Et,"transition",""),ot(Et,"transform",""),ot(Et,"box-sizing","border-box"),ot(Et,"margin",0),ot(Et,"top",t.top),ot(Et,"left",t.left),ot(Et,"width",t.width),ot(Et,"height",t.height),ot(Et,"opacity","0.8"),ot(Et,"position",li?"absolute":"fixed"),ot(Et,"zIndex","100000"),ot(Et,"pointerEvents","none"),bi.ghost=Et,e.appendChild(Et),ot(Et,"transform-origin",Wt/parseInt(Et.style.width)*100+"% "+Gt/parseInt(Et.style.height)*100+"%")}},_onDragStart:function(e,t){var i=this,a=e.dataTransfer,r=i.options;Ct("dragStart",this,{evt:e}),bi.eventCanceled?this._onDrop():(Ct("setupClone",this),bi.eventCanceled||((Pt=ft(zt)).removeAttribute("id"),Pt.draggable=!1,Pt.style["will-change"]="",this._hideClone(),rt(Pt,this.options.chosenClass,!1),bi.clone=Pt),i.cloneId=xi(function(){Ct("clone",i),bi.eventCanceled||(i.options.removeCloneOnHide||It.insertBefore(Pt,zt),i._hideClone(),At({sortable:i,name:"clone"}))}),!t&&rt(zt,r.dragClass,!0),t?(ei=!0,i._loopId=setInterval(i._emulateDragOver,50)):(Qe(document,"mouseup",i._onDrop),Qe(document,"touchend",i._onDrop),Qe(document,"touchcancel",i._onDrop),a&&(a.effectAllowed="move",r.setData&&r.setData.call(i,a,zt)),Ye(document,"drop",i),ot(zt,"transform","translateZ(0)")),Jt=!0,i._dragStartId=xi(i._dragStarted.bind(i,t,e)),Ye(document,"selectstart",i),Zt=!0,window.getSelection().removeAllRanges(),Ge&&ot(document.body,"user-select","none"))},_onDragOver:function(e){var t,i,a,r,o=this.el,n=e.target,s=this.options,l=s.group,d=bi.active,c=Vt===l,p=s.sort,g=qt||d,m=this,u=!1;if(!oi){if(void 0!==e.preventDefault&&e.cancelable&&e.preventDefault(),n=tt(n,s.draggable,o,!0),D("dragOver"),bi.eventCanceled)return u;if(zt.contains(e.target)||n.animated&&n.animatingX&&n.animatingY||m._ignoreWhileAnimating===n)return I(!1);if(ei=!1,d&&!s.disabled&&(c?p||(a=Dt!==It):qt===this||(this.lastPutMode=Vt.checkPull(this,d,zt,e))&&l.checkPut(this,d,zt,e))){if(r="vertical"===this._getDirection(e,n),t=dt(zt),D("dragOverValid"),bi.eventCanceled)return u;if(a)return Dt=It,E(),this._hideClone(),D("revert"),bi.eventCanceled||(Tt?It.insertBefore(zt,Tt):It.appendChild(zt)),I(!0);var h=gt(o,s.draggable);if(!h||function(e,t,i){var a=dt(gt(i.el,i.options.draggable)),r=yt(i.el,i.options,Et);return t?e.clientX>r.right+10||e.clientY>a.bottom&&e.clientX>a.left:e.clientY>r.bottom+10||e.clientX>a.right&&e.clientY>a.top}(e,r,this)&&!h.animated){if(h===zt)return I(!1);if(h&&o===e.target&&(n=h),n&&(i=dt(n)),!1!==fi(It,o,zt,t,n,i,e,!!n))return E(),h&&h.nextSibling?o.insertBefore(zt,h.nextSibling):o.appendChild(zt),Dt=o,T(),I(!0)}else if(h&&function(e,t,i){var a=dt(pt(i.el,0,i.options,!0)),r=yt(i.el,i.options,Et);return t?e.clientX<r.left-10||e.clientY<a.top&&e.clientX<a.right:e.clientY<r.top-10||e.clientY<a.bottom&&e.clientX<a.left}(e,r,this)){var _=pt(o,0,s,!0);if(_===zt)return I(!1);if(i=dt(n=_),!1!==fi(It,o,zt,t,n,i,e,!1))return E(),o.insertBefore(zt,_),Dt=o,T(),I(!0)}else if(n.parentNode===o){i=dt(n);var v,b,f,y=zt.parentNode!==o,w=!function(e,t,i){var a=i?e.left:e.top,r=i?e.right:e.bottom,o=i?e.width:e.height,n=i?t.left:t.top,s=i?t.right:t.bottom,l=i?t.width:t.height;return a===n||r===s||a+o/2===n+l/2}(zt.animated&&zt.toRect||t,n.animated&&n.toRect||i,r),k=r?"top":"left",x=ct(n,"top","top")||ct(zt,"top","top"),$=x?x.scrollTop:void 0;if(Kt!==n&&(b=i[k],ii=!1,ai=!w&&s.invertSwap||y),v=function(e,t,i,a,r,o,n,s){var l=a?e.clientY:e.clientX,d=a?i.height:i.width,c=a?i.top:i.left,p=a?i.bottom:i.right,g=!1;if(!n)if(s&&Yt<d*r){if(!ii&&(1===Xt?l>c+d*o/2:l<p-d*o/2)&&(ii=!0),ii)g=!0;else if(1===Xt?l<c+Yt:l>p-Yt)return-Xt}else if(l>c+d*(1-r)/2&&l<p-d*(1-r)/2)return function(e){return mt(zt)<mt(e)?1:-1}(t);return(g=g||n)&&(l<c+d*o/2||l>p-d*o/2)?l>c+d/2?1:-1:0}(e,n,i,r,w?1:s.swapThreshold,null==s.invertedSwapThreshold?s.swapThreshold:s.invertedSwapThreshold,ai,Kt===n),0!==v){var S=mt(zt);do{S-=v,f=Dt.children[S]}while(f&&("none"===ot(f,"display")||f===Et))}if(0===v||f===n)return I(!1);Kt=n,Xt=v;var C=n.nextElementSibling,A=!1,z=fi(It,o,zt,t,n,i,e,A=1===v);if(!1!==z)return 1!==z&&-1!==z||(A=1===z),oi=!0,setTimeout(wi,30),E(),A&&!C?o.appendChild(zt):n.parentNode.insertBefore(zt,A?C:n),x&&bt(x,0,$-x.scrollTop),Dt=zt.parentNode,void 0===b||ai||(Yt=Math.abs(b-dt(n)[k])),T(),I(!0)}if(o.contains(zt))return I(!1)}return!1}function D(s,l){Ct(s,m,qe({evt:e,isOwner:c,axis:r?"vertical":"horizontal",revert:a,dragRect:t,targetRect:i,canSort:p,fromSortable:g,target:n,completed:I,onMove:function(i,a){return fi(It,o,zt,t,i,dt(i),e,a)},changed:T},l))}function E(){D("dragOverAnimationCapture"),m.captureAnimationState(),m!==g&&g.captureAnimationState()}function I(t){return D("dragOverCompleted",{insertion:t}),t&&(c?d._hideClone():d._showClone(m),m!==g&&(rt(zt,qt?qt.options.ghostClass:d.options.ghostClass,!1),rt(zt,s.ghostClass,!0)),qt!==m&&m!==bi.active?qt=m:m===bi.active&&qt&&(qt=null),g===m&&(m._ignoreWhileAnimating=n),m.animateAll(function(){D("dragOverAnimationComplete"),m._ignoreWhileAnimating=null}),m!==g&&(g.animateAll(),g._ignoreWhileAnimating=null)),(n===zt&&!zt.animated||n===o&&!n.animated)&&(Kt=null),s.dragoverBubble||e.rootEl||n===document||(zt.parentNode[wt]._isOutsideThisEl(e.target),!t&&_i(e)),!s.dragoverBubble&&e.stopPropagation&&e.stopPropagation(),u=!0}function T(){Mt=mt(zt),Lt=mt(zt,s.draggable),At({sortable:m,name:"change",toEl:o,newIndex:Mt,newDraggableIndex:Lt,originalEvent:e})}},_ignoreWhileAnimating:null,_offMoveEvents:function(){Qe(document,"mousemove",this._onTouchMove),Qe(document,"touchmove",this._onTouchMove),Qe(document,"pointermove",this._onTouchMove),Qe(document,"dragover",_i),Qe(document,"mousemove",_i),Qe(document,"touchmove",_i)},_offUpEvents:function(){var e=this.el.ownerDocument;Qe(e,"mouseup",this._onDrop),Qe(e,"touchend",this._onDrop),Qe(e,"pointerup",this._onDrop),Qe(e,"pointercancel",this._onDrop),Qe(e,"touchcancel",this._onDrop),Qe(document,"selectstart",this)},_onDrop:function(e){var t=this.el,i=this.options;Mt=mt(zt),Lt=mt(zt,i.draggable),Ct("drop",this,{evt:e}),Dt=zt&&zt.parentNode,Mt=mt(zt),Lt=mt(zt,i.draggable),bi.eventCanceled||(Jt=!1,ai=!1,ii=!1,clearInterval(this._loopId),clearTimeout(this._dragStartTimer),$i(this.cloneId),$i(this._dragStartId),this.nativeDraggable&&(Qe(document,"drop",this),Qe(t,"dragstart",this._onDragStart)),this._offMoveEvents(),this._offUpEvents(),Ge&&ot(document.body,"user-select",""),ot(zt,"transform",""),e&&(Zt&&(e.cancelable&&e.preventDefault(),!i.dropBubble&&e.stopPropagation()),Et&&Et.parentNode&&Et.parentNode.removeChild(Et),(It===Dt||qt&&"clone"!==qt.lastPutMode)&&Pt&&Pt.parentNode&&Pt.parentNode.removeChild(Pt),zt&&(this.nativeDraggable&&Qe(zt,"dragend",this),yi(zt),zt.style["will-change"]="",Zt&&!Jt&&rt(zt,qt?qt.options.ghostClass:this.options.ghostClass,!1),rt(zt,this.options.chosenClass,!1),At({sortable:this,name:"unchoose",toEl:Dt,newIndex:null,newDraggableIndex:null,originalEvent:e}),It!==Dt?(Mt>=0&&(At({rootEl:Dt,name:"add",toEl:Dt,fromEl:It,originalEvent:e}),At({sortable:this,name:"remove",toEl:Dt,originalEvent:e}),At({rootEl:Dt,name:"sort",toEl:Dt,fromEl:It,originalEvent:e}),At({sortable:this,name:"sort",toEl:Dt,originalEvent:e})),qt&&qt.save()):Mt!==Nt&&Mt>=0&&(At({sortable:this,name:"update",toEl:Dt,originalEvent:e}),At({sortable:this,name:"sort",toEl:Dt,originalEvent:e})),bi.active&&(null!=Mt&&-1!==Mt||(Mt=Nt,Lt=jt),At({sortable:this,name:"end",toEl:Dt,originalEvent:e}),this.save())))),this._nulling()},_nulling:function(){Ct("nulling",this),It=zt=Dt=Et=Tt=Pt=Rt=Ht=Ot=Bt=Zt=Mt=Lt=Nt=jt=Kt=Xt=qt=Vt=bi.dragged=bi.ghost=bi.clone=bi.active=null;var e=this.el;ni.forEach(function(t){e.contains(t)&&(t.checked=!0)}),ni.length=Ut=Ft=0},handleEvent:function(e){switch(e.type){case"drop":case"dragend":this._onDrop(e);break;case"dragenter":case"dragover":zt&&(this._onDragOver(e),function(e){e.dataTransfer&&(e.dataTransfer.dropEffect="move"),e.cancelable&&e.preventDefault()}(e));break;case"selectstart":e.preventDefault()}},toArray:function(){for(var e,t=[],i=this.el.children,a=0,r=i.length,o=this.options;a<r;a++)tt(e=i[a],o.draggable,this.el,!1)&&t.push(e.getAttribute(o.dataIdAttr)||ki(e));return t},sort:function(e,t){var i={},a=this.el;this.toArray().forEach(function(e,t){var r=a.children[t];tt(r,this.options.draggable,a,!1)&&(i[e]=r)},this),t&&this.captureAnimationState(),e.forEach(function(e){i[e]&&(a.removeChild(i[e]),a.appendChild(i[e]))}),t&&this.animateAll()},save:function(){var e=this.options.store;e&&e.set&&e.set(this)},closest:function(e,t){return tt(e,t||this.options.draggable,this.el,!1)},option:function(e,t){var i=this.options;if(void 0===t)return i[e];var a=$t.modifyOption(this,e,t);i[e]=void 0!==a?a:t,"group"===e&&mi(i)},destroy:function(){Ct("destroy",this);var e=this.el;e[wt]=null,Qe(e,"mousedown",this._onTapStart),Qe(e,"touchstart",this._onTapStart),Qe(e,"pointerdown",this._onTapStart),this.nativeDraggable&&(Qe(e,"dragover",this),Qe(e,"dragenter",this)),Array.prototype.forEach.call(e.querySelectorAll("[draggable]"),function(e){e.removeAttribute("draggable")}),this._onDrop(),this._disableDelayedDragEvents(),ti.splice(ti.indexOf(this.el),1),this.el=e=null},_hideClone:function(){if(!Ht){if(Ct("hideClone",this),bi.eventCanceled)return;ot(Pt,"display","none"),this.options.removeCloneOnHide&&Pt.parentNode&&Pt.parentNode.removeChild(Pt),Ht=!0}},_showClone:function(e){if("clone"===e.lastPutMode){if(Ht){if(Ct("showClone",this),bi.eventCanceled)return;zt.parentNode!=It||this.options.group.revertClone?Tt?It.insertBefore(Pt,Tt):It.appendChild(Pt):It.insertBefore(Pt,zt),this.options.group.revertClone&&this.animate(zt,Pt),ot(Pt,"display",""),Ht=!1}}else this._hideClone()}},si&&Ye(document,"touchmove",function(e){(bi.active||Jt)&&e.cancelable&&e.preventDefault()}),bi.utils={on:Ye,off:Qe,css:ot,find:st,is:function(e,t){return!!tt(e,t,e,!1)},extend:function(e,t){if(e&&t)for(var i in t)t.hasOwnProperty(i)&&(e[i]=t[i]);return e},throttle:vt,closest:tt,toggleClass:rt,clone:ft,index:mt,nextTick:xi,cancelNextTick:$i,detectDirection:gi,getChild:pt,expando:wt},bi.get=function(e){return e[wt]},bi.mount=function(){for(var e=arguments.length,t=new Array(e),i=0;i<e;i++)t[i]=arguments[i];t[0].constructor===Array&&(t=t[0]),t.forEach(function(e){if(!e.prototype||!e.prototype.constructor)throw"Sortable: Mounted plugin must be a constructor function, not ".concat({}.toString.call(e));e.utils&&(bi.utils=qe(qe({},bi.utils),e.utils)),$t.mount(e)})},bi.create=function(e,t){return new bi(e,t)},bi.version="1.15.7";var Si,Ci,Ai,zi,Di,Ei,Ii=[],Ti=!1;function Ri(){Ii.forEach(function(e){clearInterval(e.pid)}),Ii=[]}function Pi(){clearInterval(Ei)}var Hi=vt(function(e,t,i,a){if(t.scroll){var r,o=(e.touches?e.touches[0]:e).clientX,n=(e.touches?e.touches[0]:e).clientY,s=t.scrollSensitivity,l=t.scrollSpeed,d=lt(),c=!1;Ci!==i&&(Ci=i,Ri(),Si=t.scroll,r=t.scrollFn,!0===Si&&(Si=ht(i,!0)));var p=0,g=Si;do{var m=g,u=dt(m),h=u.top,_=u.bottom,v=u.left,b=u.right,f=u.width,y=u.height,w=void 0,k=void 0,x=m.scrollWidth,$=m.scrollHeight,S=ot(m),C=m.scrollLeft,A=m.scrollTop;m===d?(w=f<x&&("auto"===S.overflowX||"scroll"===S.overflowX||"visible"===S.overflowX),k=y<$&&("auto"===S.overflowY||"scroll"===S.overflowY||"visible"===S.overflowY)):(w=f<x&&("auto"===S.overflowX||"scroll"===S.overflowX),k=y<$&&("auto"===S.overflowY||"scroll"===S.overflowY));var z=w&&(Math.abs(b-o)<=s&&C+f<x)-(Math.abs(v-o)<=s&&!!C),D=k&&(Math.abs(_-n)<=s&&A+y<$)-(Math.abs(h-n)<=s&&!!A);if(!Ii[p])for(var E=0;E<=p;E++)Ii[E]||(Ii[E]={});Ii[p].vx==z&&Ii[p].vy==D&&Ii[p].el===m||(Ii[p].el=m,Ii[p].vx=z,Ii[p].vy=D,clearInterval(Ii[p].pid),0==z&&0==D||(c=!0,Ii[p].pid=setInterval(function(){a&&0===this.layer&&bi.active._onTouchMove(Di);var t=Ii[this.layer].vy?Ii[this.layer].vy*l:0,i=Ii[this.layer].vx?Ii[this.layer].vx*l:0;"function"==typeof r&&"continue"!==r.call(bi.dragged.parentNode[wt],i,t,e,Di,Ii[this.layer].el)||bt(Ii[this.layer].el,i,t)}.bind({layer:p}),24))),p++}while(t.bubbleScroll&&g!==d&&(g=ht(g,!1)));Ti=c}},30),Ni=function(e){var t=e.originalEvent,i=e.putSortable,a=e.dragEl,r=e.activeSortable,o=e.dispatchSortableEvent,n=e.hideGhostForTarget,s=e.unhideGhostForTarget;if(t){var l=i||r;n();var d=t.changedTouches&&t.changedTouches.length?t.changedTouches[0]:t,c=document.elementFromPoint(d.clientX,d.clientY);s(),l&&!l.el.contains(c)&&(o("spill"),this.onSpill({dragEl:a,putSortable:i}))}};function Mi(){}function ji(){}Mi.prototype={startIndex:null,dragStart:function(e){var t=e.oldDraggableIndex;this.startIndex=t},onSpill:function(e){var t=e.dragEl,i=e.putSortable;this.sortable.captureAnimationState(),i&&i.captureAnimationState();var a=pt(this.sortable.el,this.startIndex,this.options);a?this.sortable.el.insertBefore(t,a):this.sortable.el.appendChild(t),this.sortable.animateAll(),i&&i.animateAll()},drop:Ni},Le(Mi,{pluginName:"revertOnSpill"}),ji.prototype={onSpill:function(e){var t=e.dragEl,i=e.putSortable||this.sortable;i.captureAnimationState(),t.parentNode&&t.parentNode.removeChild(t),i.animateAll()},drop:Ni},Le(ji,{pluginName:"removeOnSpill"}),bi.mount(new function(){function e(){for(var e in this.defaults={scroll:!0,forceAutoScrollFallback:!1,scrollSensitivity:30,scrollSpeed:10,bubbleScroll:!0},this)"_"===e.charAt(0)&&"function"==typeof this[e]&&(this[e]=this[e].bind(this))}return e.prototype={dragStarted:function(e){var t=e.originalEvent;this.sortable.nativeDraggable?Ye(document,"dragover",this._handleAutoScroll):this.options.supportPointer?Ye(document,"pointermove",this._handleFallbackAutoScroll):t.touches?Ye(document,"touchmove",this._handleFallbackAutoScroll):Ye(document,"mousemove",this._handleFallbackAutoScroll)},dragOverCompleted:function(e){var t=e.originalEvent;this.options.dragOverBubble||t.rootEl||this._handleAutoScroll(t)},drop:function(){this.sortable.nativeDraggable?Qe(document,"dragover",this._handleAutoScroll):(Qe(document,"pointermove",this._handleFallbackAutoScroll),Qe(document,"touchmove",this._handleFallbackAutoScroll),Qe(document,"mousemove",this._handleFallbackAutoScroll)),Pi(),Ri(),clearTimeout(it),it=void 0},nulling:function(){Di=Ci=Si=Ti=Ei=Ai=zi=null,Ii.length=0},_handleFallbackAutoScroll:function(e){this._handleAutoScroll(e,!0)},_handleAutoScroll:function(e,t){var i=this,a=(e.touches?e.touches[0]:e).clientX,r=(e.touches?e.touches[0]:e).clientY,o=document.elementFromPoint(a,r);if(Di=e,t||this.options.forceAutoScrollFallback||Fe||Ue||Ge){Hi(e,this.options,o,t);var n=ht(o,!0);!Ti||Ei&&a===Ai&&r===zi||(Ei&&Pi(),Ei=setInterval(function(){var o=ht(document.elementFromPoint(a,r),!0);o!==n&&(n=o,Ri()),Hi(e,i.options,o,t)},10),Ai=a,zi=r)}else{if(!this.options.bubbleScroll||ht(o,!0)===lt())return void Ri();Hi(e,this.options,ht(o,!1),!1)}}},Le(e,{pluginName:"scroll",initializeByDefault:!0})}),bi.mount(ji,Mi);const Li=n`
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 500;
        font-family: inherit;
        color: var(--primary-color);
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        transition: background 150ms ease, color 150ms ease,
                    border-color 150ms ease, box-shadow 300ms ease;
    }
    .action-btn:hover {
        background: var(--secondary-background-color);
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* Semantic chip colors -- the one palette, everywhere. */
    .action-btn.assign-btn {
        color: #2e7d32;
        border-color: rgba(46, 125, 50, 0.3);
        position: relative; /* anchor for the green assignment dot */
    }
    .action-btn.assign-btn:hover {
        background: rgba(46, 125, 50, 0.08);
    }
    .action-btn.test-btn {
        color: var(--primary-color);
    }
    .action-btn.trigger-btn {
        color: #b89930;
        border-color: rgba(184, 153, 48, 0.3);
        position: relative; /* anchor for the yellow trigger dot */
    }
    .action-btn.trigger-btn:hover {
        background: rgba(184, 153, 48, 0.08);
    }
    .action-btn.delete-btn {
        color: #e65100;
        border-color: rgba(230, 81, 0, 0.25);
    }
    .action-btn.delete-btn:hover {
        background: rgba(230, 81, 0, 0.08);
    }
    .action-btn.dismiss-btn {
        color: var(--secondary-text-color);
        border-color: var(--divider-color);
        position: relative; /* anchor for the dot indicator */
    }
`;let Vi=class extends se{constructor(){super(...arguments),this.color="green",this.count=0}render(){if(this.count<1)return B``;const e=this.count>=10;return B`<span
            class="dot badge ${this.color} ${e?"multi-digit":""}"
            ><span class="digit">${this.count}</span></span
        >`}};Vi.styles=n`
        /* The host generates no box; each dot is absolutely positioned against
           the calling button (which sets position: relative). This keeps the
           dot out of inline flow, so a numbered badge cannot pick up a
           line-box strut and drift downward the way an inline-flex child does. */
        :host {
            display: contents;
        }
        .dot {
            position: absolute;
            pointer-events: none;
            box-shadow: 0 0 0 1.5px var(--card-background-color);
        }
        /* Numbered 10px badge for count 1..9. Anchored at -5 so the box
           centres on the button's top-right corner point. (A bare unnumbered
           dot for count 1 existed through v0.6.1; retired on the v0.6.6
           bench -- every count shows its number now.) */
        .dot.badge {
            top: -5px;
            right: -5px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            color: #ffffff;
            /* 8px (not 7px) rasterises crisply at this size and reads as
               centred; 7px snapped to the pixel grid and looked off. */
            font-size: 8px;
            font-weight: 500;
            line-height: 1;
            /* The action buttons set letter-spacing, which inherits here and
               adds phantom space to the RIGHT of the single digit -- the flex
               box then centres [digit + that space], shoving the digit left.
               Reset it so the digit centres on its own advance. */
            letter-spacing: normal;
            /* Every numeral on the same uniform advance width, so 1, 2,
               and 9 all land at the identical spot in the circle. Without
               this, each digit centres on its own advance and the dots
               visibly disagree with each other (owner bench, shampoo). */
            font-variant-numeric: tabular-nums;
        }
        /* Optical centring for the digit's shared bias: half a pixel right
           and half down from true flex centre (subpixel transforms render
           antialiased -- dialled on the bench across three passes). With
           tabular-nums above, this one value holds for every digit. */
        .dot.badge .digit {
            display: block;
            transform: translate(0.5px, 0.5px);
        }
        /* Double-digit stretch for count >= 10 (wider pill, pulled out a touch
           further so it clears the corner). */
        .dot.badge.multi-digit {
            right: -6px;
            min-width: 10px;
            padding: 0 3px;
            border-radius: 5px;
        }
        /* Colour variants */
        .dot.green {
            background: #2e7d32;
        }
        .dot.yellow {
            background: #b89930;
        }
    `,e([pe({type:String})],Vi.prototype,"color",void 0),e([pe({type:Number})],Vi.prototype,"count",void 0),Vi=e([ue("ir-count-dot")],Vi);let qi=class extends se{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1,this.actionLabel=null,this.hasTrigger=!1,this.triggerCount=0,this.showActionMapping=!0,this._editingName=!1,this._draftName=""}_commandLabel(){const e=this.command;return e.protocol&&e.code?`${e.protocol}: ${e.code}`:e.raw_timings?.length?ke("cmdrow.raw_timings",{count:e.raw_timings.length}):e.protocol??"IR"}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),a=t.slice(4);if(a.length<2*i)return null;const r=[];for(let e=0;e<2*i;e++){const t=parseInt(a[e],16);r.push(t>=48)}return r.length>0?r:null}_renderDiamonds(){const e=this.command;if(!e||"PRONTO"!==e.protocol?.toUpperCase()||!e.code)return null;const t=this._prontoSlArray(e.code);return t?B`<span class="diamonds">${t.map(e=>e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}</span>`:null}_emit(e,t){const i=t?.currentTarget?.getBoundingClientRect()??null;this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command,buttonRect:i},bubbles:!0,composed:!0}))}_startRename(e){this.command&&!this.busy&&(e.stopPropagation(),this._draftName=this.command.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()}))}_commitRename(){if(!this._editingName)return;const e=this._draftName.trim();this._editingName=!1,this.command&&e&&e!==this.command.name&&this.dispatchEvent(new CustomEvent("rename-command",{detail:{command:this.command,name:e},bubbles:!0,composed:!0}))}_onRenameKeydown(e){"Enter"===e.key?(e.preventDefault(),this._commitRename()):"Escape"===e.key&&(this._editingName=!1)}render(){const e=null!==this.command,t=e?this._renderDiamonds():null;return B`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    <slot name="status"></slot>
                </div>
                <div class="info">
                    <div class="name">
                        ${e?this._editingName?B`<input
                                      class="name-input"
                                      type="text"
                                      .value=${this._draftName}
                                      @input=${e=>this._draftName=e.target.value}
                                      @keydown=${this._onRenameKeydown}
                                      @blur=${this._commitRename}
                                  />`:B`<span
                                      class="editable-name"
                                      title=${ke("cmdrow.rename")}
                                      @click=${this._startRename}
                                      >${this.templateName}<span class="rename-pencil"
                                          >&#9998;</span
                                      ></span
                                  >`:B`${this.templateName}`}
                        ${e&&this.command?.decoded_fingerprint?B`<button
                                  class="tx-pill ${this.command.tx_force_raw?"tx-raw-on":""}"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("toggle-tx-raw")}
                                  title=${this.command.tx_force_raw?ke("cmdrow.tx_raw_on"):ke("cmdrow.tx_raw_off")}
                              >${this.command.tx_force_raw?"PRONTO":this.command.decoded_protocol??"AUTO"}</button>`:""}
                        ${e&&this.command&&this.command.send_count>1?B`<span
                                  class="repeat-indicator"
                                  title=${ke("cmdrow.sends_times",{count:this.command.send_count})}
                                  ><ha-svg-icon
                                      .path=${"M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"}
                                  ></ha-svg-icon
                                  >${this.command.send_count}</span
                              >`:""}
                        ${e&&this.command&&this.command.repeat_count>1&&this.command.decoded_protocol&&!this.command.tx_force_raw?B`<span
                                  class="ditto-indicator"
                                  title=${ke("cmdrow.dittos",{count:this.command.repeat_count})}
                                  ><ha-svg-icon
                                      .path=${"M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z"}
                                  ></ha-svg-icon
                                  >${this.command.repeat_count}</span
                              >`:""}
                    </div>
                    <div class="meta">
                        ${t||(e?B`${this._commandLabel()}`:B`<span class="muted">${ke("cmdrow.not_learned")}</span>`)}
                    </div>
                </div>
                <div class="actions">
                    ${e?B`
                              <button
                                  class="icon-btn edit-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("edit-command")}
                                  title=${ke("cmdrow.edit_code")}
                              ><ha-svg-icon
                                      class="edit-glyph"
                                      .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                  ></ha-svg-icon></button>
                              ${this.showActionMapping?B`<button
                                  class="action-btn badge-btn"
                                  ?data-mapped=${!!this.actionLabel}
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("map-action")}
                                  title=${ke("cmdrow.map_action")}
                              >${this.actionLabel||ke("cmdrow.actions")}</button>`:""}
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >${ke("cmdrow.test")}</button>
                              <button
                                  class="action-btn trigger-btn"
                                  ?disabled=${this.busy}
                                  @click=${e=>this._emit("toggle-trigger",e)}
                                  title=${this.hasTrigger?ke("cmdrow.edit_trigger"):ke("cmdrow.create_trigger")}
                              >${ke("cmdrow.trigger")}<ir-count-dot
                                      color="yellow"
                                      .count=${this.triggerCount||(this.hasTrigger?1:0)}
                                  ></ir-count-dot></button>
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                              >${ke("cmdrow.delete")}</button>
                          `:B`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >${ke("cmdrow.learn")}</button>
                          `}
                </div>
            </div>
        `}};qi.styles=n`
        :host {
            display: block;
        }
        :host(:not(:last-of-type)) {
            margin-bottom: 4px;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 8px 10px;
            /* Match the page background so the long horizontal command
               strips visually merge with the device-detail backdrop
               instead of reading as highlighted bands. Themes that
               distinguish primary vs secondary background colors will
               carry both through naturally; themes that keep them
               equal end up with the same visual effect. The hover
               state on action buttons inside the row still uses
               --secondary-background-color so the button hover remains
               distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .name {
            display: flex;
            align-items: center;
            gap: 7px;
            flex-wrap: wrap;
            font-weight: 500;
        }
        .editable-name {
            cursor: pointer;
            position: relative;
            display: inline-flex;
            align-items: center;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .rename-pencil {
            /* Out of layout flow so it reserves no width: the name-to-pill
               gap stays the true 7px flex gap (matches pill-to-count).
               Tucked over the tail of the name; fades in on hover and never
               reaches the pill. */
            position: absolute;
            left: 100%;
            top: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .rename-pencil {
            opacity: 1;
        }
        .name-input {
            font-size: inherit;
            font-weight: 500;
            font-family: inherit;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            padding: 0 0 1px;
            min-width: 120px;
        }
        .repeat-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            /* Match the short-diamond orange; bare (no pill) on the name line.
               Vertically centered in line with the pill via the name flex.
               Slight knock-down to sit softer next to the pill. */
            color: var(--warning-color, #ff9800);
            opacity: 0.85;
        }
        .repeat-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
        }
        .ditto-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            /* Match the long-diamond blue (decoded protocol); same size as the
               orange send-count indicator it sits beside. */
            color: var(--primary-color);
            opacity: 0.85;
        }
        .ditto-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
        }
        .icon-btn {
            background: none;
            border: none;
            padding: 2px;
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            color: var(--secondary-text-color);
        }
        .icon-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .icon-btn:hover:not(:disabled) {
            color: var(--primary-text-color);
        }
        .edit-glyph {
            --mdc-icon-size: 10px;
        }
        .meta {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: var(--code-font-family, monospace);
        }
        .muted {
            font-style: italic;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            color: var(--primary-color);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .action-btn.test-btn {
            color: #2e7d32;
            border-color: rgba(46, 125, 50, 0.3);
        }
        .action-btn.test-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .action-btn.learn-btn {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
        }
        .action-btn.learn-btn:hover {
            background: #1b5e20;
        }
        .action-btn.badge-btn {
            color: var(--secondary-text-color, #999);
            border-color: var(--divider-color);
            min-width: 50px;
            text-align: center;
        }
        .action-btn.badge-btn[data-mapped] {
            color: var(--primary-color);
            border-color: var(--primary-color);
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.08);
        }
        .action-btn.badge-btn:hover {
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.12);
        }
        .action-btn.trigger-btn {
            position: relative;
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
        /* Protocol toggle on the name line: a tiny solid pill with white
           text. Blue fill = decoded protocol (NEC); orange fill = the
           captured-replay (PRONTO) override. Same tx_force_raw toggle. */
        .tx-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            height: 11px;
            border: none;
            border-radius: 999px;
            /* Slightly more top than bottom pad to optically center the caps. */
            padding: 1px 5px 0;
            font-size: 9px;
            font-weight: 500;
            font-family: inherit;
            letter-spacing: 0.03em;
            line-height: 1;
            color: #fff;
            /* Soften the fill (not the whole pill) so the white text stays
               crisp while the hue reads lighter / less poppy than the diamonds. */
            background: color-mix(in srgb, var(--primary-color) 82%, transparent);
            cursor: pointer;
            transition: opacity 150ms ease;
        }
        .tx-pill.tx-raw-on {
            /* Match the short-diamond orange, softened the same amount. */
            background: color-mix(in srgb, var(--warning-color, #ff9800) 82%, transparent);
        }
        .tx-pill:hover:not(:disabled) {
            opacity: 0.85;
        }
        .tx-pill:disabled {
            opacity: 0.5;
            cursor: default;
        }
    `,e([pe({attribute:!1})],qi.prototype,"templateName",void 0),e([pe({attribute:!1})],qi.prototype,"command",void 0),e([pe({type:Boolean})],qi.prototype,"busy",void 0),e([pe({attribute:!1})],qi.prototype,"actionLabel",void 0),e([pe({type:Boolean})],qi.prototype,"hasTrigger",void 0),e([pe({type:Number})],qi.prototype,"triggerCount",void 0),e([pe({type:Boolean})],qi.prototype,"showActionMapping",void 0),e([ge()],qi.prototype,"_editingName",void 0),e([ge()],qi.prototype,"_draftName",void 0),qi=e([ue("ir-command-row")],qi);let Oi=class extends se{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return B`
            <div class="phase listening" aria-live="polite">
                <div class="pulse" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div class="title">${ke("capture.listening")}</div>
                <div class="instruction">
                    ${ke("capture.instruction",{name:this.commandName})}
                </div>
                <div class="countdown">
                    ${ke("capture.remaining",{seconds:this._timeRemaining})}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._cancel}>${ke("common.cancel")}</mwc-button>
                </div>
            </div>
        `}_renderCaptured(){const e=this._result;return B`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">${ke("capture.captured")}</div>
                <div class="meta">
                    ${ke("capture.protocol",{protocol:e.protocol??ke("capture.protocol_raw")})}${e.code?B` · <code>${e.code}</code>`:""}
                </div>
                <ha-alert alert-type="info">
                    ${ke("capture.verify")}
                </ha-alert>
                <div class="actions">
                    <mwc-button @click=${this._testCommand}>${ke("capture.test")}</mwc-button>
                    <mwc-button @click=${this._recapture}>${ke("capture.recapture")}</mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        ${ke("capture.save_next")}
                    </mwc-button>
                </div>
            </div>
        `}_renderTimeout(){return B`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${ke("capture.no_signal")}</div>
                <ul class="tips">
                    <li>${ke("capture.tip_point")}</li>
                    <li>${ke("capture.tip_closer")}</li>
                    <li>${ke("capture.tip_hold")}</li>
                </ul>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>${ke("capture.try_again")}</mwc-button>
                    <mwc-button @click=${this._cancel}>${ke("common.cancel")}</mwc-button>
                </div>
            </div>
        `}_renderDuplicate(){const e=this._result;return B`
            <div class="phase warning" aria-live="assertive">
                <div class="title warn">${ke("capture.duplicate")}</div>
                <div class="instruction">
                    ${ke("capture.duplicate_instruction",{name:this._duplicate.name})}
                </div>
                <div class="meta">
                    ${ke("capture.protocol",{protocol:e.protocol??ke("capture.protocol_raw")})}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._recapture}>
                        ${ke("capture.recapture_different")}
                    </mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        ${ke("capture.save_anyway")}
                    </mwc-button>
                </div>
            </div>
        `}_renderError(){return B`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${ke("capture.error")}</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>
                        ${ke("capture.try_again")}
                    </mwc-button>
                    <mwc-button @click=${this._cancel}>${ke("common.cancel")}</mwc-button>
                </div>
            </div>
        `}render(){return B`
            <ha-dialog
                open
                heading=${ke("capture.learning",{name:this.commandName})}
                @closed=${this._cancel}
            >
                ${"listening"===this._phase?this._renderListening():"captured"===this._phase?this._renderCaptured():"timeout"===this._phase?this._renderTimeout():"duplicate"===this._phase?this._renderDuplicate():this._renderError()}
            </ha-dialog>
        `}};Oi.styles=n`
        .phase {
            min-width: 320px;
            padding: 8px 0;
        }
        .title {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .title.warn {
            color: var(--warning-color, #ffa600);
        }
        .instruction {
            color: var(--primary-text-color);
            margin-bottom: 8px;
        }
        .meta {
            color: var(--secondary-text-color);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        .countdown {
            margin: 10px 0;
            font-variant-numeric: tabular-nums;
            color: var(--secondary-text-color);
        }
        .check {
            font-size: 3rem;
            color: var(--success-color, #43a047);
            text-align: center;
            margin: 8px 0;
        }
        .pulse {
            display: flex;
            justify-content: center;
            gap: 6px;
            margin: 8px 0 16px;
        }
        .pulse span {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: var(--primary-color);
            border-radius: 50%;
            opacity: 0.4;
            animation: pulse 1s infinite ease-in-out;
        }
        .pulse span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .pulse span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes pulse {
            0%,
            100% {
                opacity: 0.3;
                transform: scale(0.85);
            }
            50% {
                opacity: 1;
                transform: scale(1.1);
            }
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        .tips {
            margin: 4px 0 12px;
            padding-left: 22px;
            color: var(--primary-text-color);
        }
    `,e([pe({attribute:!1})],Oi.prototype,"api",void 0),e([pe({attribute:!1})],Oi.prototype,"hass",void 0),e([pe({attribute:!1})],Oi.prototype,"device",void 0),e([pe({attribute:!1})],Oi.prototype,"commandName",void 0),e([pe({attribute:!1})],Oi.prototype,"timeout",void 0),e([ge()],Oi.prototype,"_phase",void 0),e([ge()],Oi.prototype,"_result",void 0),e([ge()],Oi.prototype,"_duplicate",void 0),e([ge()],Oi.prototype,"_error",void 0),e([ge()],Oi.prototype,"_timeRemaining",void 0),e([ge()],Oi.prototype,"_sessionId",void 0),Oi=e([ue("ir-capture-dialog")],Oi);const Bi=n`
    /* --- Custom overlay shell (dialogs not hosted in <ha-dialog>) --- */
    .overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }
    .dialog {
        background: var(--card-background-color, #fff);
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .heading {
        margin: 0 0 16px;
        font-size: 1.1rem;
        font-weight: 500;
        color: var(--primary-text-color);
    }

    /* --- Form fields --- */
    .field {
        display: block;
        margin: 12px 0;
        width: 100%;
    }
    .field label {
        display: block;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
    }
    input[type="text"],
    select {
        width: 100%;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 0.95rem;
        font-family: inherit;
        box-sizing: border-box;
    }
    input[type="text"]:focus,
    select:focus {
        outline: none;
        border-color: var(--primary-color);
    }

    /* --- Actions row --- */
    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color);
    }

    /* --- Action buttons: outlined family (the majority) --- */
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        transition: background 150ms ease;
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* --- Action buttons: solid borderless family (assign/promote) --- */
    .action-btn.wide {
        padding: 8px 20px;
        font-size: 0.9rem;
        border: none;
        transition: background 150ms ease, opacity 150ms ease;
    }
    .action-btn.wide:disabled {
        cursor: not-allowed;
    }

    /* --- The cancel button, identical everywhere --- */
    .cancel-btn {
        background: transparent;
        color: var(--secondary-text-color);
    }
    .cancel-btn:hover:not(:disabled) {
        background: var(--secondary-background-color);
    }
`;let Ui=class extends se{constructor(){super(...arguments),this.title="",this.message="",this.confirmLabel="",this.cancelLabel="",this.destructive=!1,this._busy=!1}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_confirm(){this.dispatchEvent(new CustomEvent("confirmed",{bubbles:!0,composed:!0}))}render(){return B`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">${this.title||ke("common.confirm")}</h3>
                    <p class="message">${this.message||ke("common.are_you_sure")}</p>
                    <div class="actions">
                        <button class="btn cancel" @click=${this._close}>
                            ${this.cancelLabel||ke("common.cancel")}
                        </button>
                        <button
                            class="btn confirm ${this.destructive?"destructive":""}"
                            @click=${this._confirm}
                        >
                            ${this.confirmLabel||ke("common.confirm")}
                        </button>
                    </div>
                </div>
            </div>
        `}};Ui.styles=[Bi,n`
        /* Tighter heading than the shared 16px; ships this way. */
        .heading {
            margin: 0 0 12px;
        }
        .message {
            margin: 0 0 20px;
            color: var(--secondary-text-color);
            line-height: 1.5;
            font-size: 0.95rem;
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        .confirm {
            color: #fff;
            background: var(--primary-color);
            border-color: var(--primary-color);
        }
        .confirm:hover {
            opacity: 0.9;
        }
        .confirm.destructive {
            background: #e65100;
            border-color: #e65100;
        }
    `],e([pe()],Ui.prototype,"title",void 0),e([pe()],Ui.prototype,"message",void 0),e([pe()],Ui.prototype,"confirmLabel",void 0),e([pe()],Ui.prototype,"cancelLabel",void 0),e([pe({type:Boolean})],Ui.prototype,"destructive",void 0),e([ge()],Ui.prototype,"_busy",void 0),Ui=e([ue("ir-confirm-dialog")],Ui);let Fi=class extends se{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.excludeEntityIds=[],this._didAutoSelect=!1,this._receiverIds=new Set,this._receiversLoaded=!1}updated(e){if(super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers()),!this._didAutoSelect)if(this.value.length>0)this._didAutoSelect=!0;else{const e=this._getEmitters();1===e.length&&(this._didAutoSelect=!0,this._fireChange([e[0].entity_id]))}}async _loadReceivers(){if(this.api)try{const e=await this.api.listReceivers();this._receiverIds=new Set(e.map(e=>e.entity_id))}catch{this._receiverIds=new Set}}_getEmitters(){const e=this.hass?.states??{},t=new Set(this.excludeEntityIds),i=[];for(const[a,r]of Object.entries(e))!a.startsWith("infrared.")||t.has(a)||this._receiverIds.has(a)||r.attributes.hair_observer||i.push({entity_id:a,name:r.attributes.friendly_name??a});return i}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._getEmitters(),t=e.filter(e=>!this.value.includes(e.entity_id));return B`
            <label>${ke("picker.emitters_label")}</label>

            ${this.value.length>0?B`
                      <div class="chips">
                          ${this.value.map(e=>B`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(e)}</span>
                                      ${this.disabled?"":B`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title=${ke("common.remove")}
                                            >&times;</button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===e.length?B`<div class="no-emitters">${ke("picker.no_emitters")}</div>`:t.length>0?B`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">${ke("picker.add_emitter")}</option>
                            ${t.map(e=>B`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:this.value.length>0?B`<div class="all-selected">${ke("picker.all_emitters_selected")}</div>`:""}
        `}};Fi.styles=n`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--secondary-background-color);
            color: #ff9800;
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
            line-height: 1;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chip-remove {
            background: none;
            border: none;
            color: inherit;
            font-size: 1rem;
            cursor: pointer;
            padding: 0 2px;
            line-height: 1;
            opacity: 0.65;
            transition: opacity 120ms ease;
        }
        .chip-remove:hover {
            opacity: 1;
        }
        select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,e([pe({attribute:!1})],Fi.prototype,"hass",void 0),e([pe({attribute:!1})],Fi.prototype,"api",void 0),e([pe({attribute:!1})],Fi.prototype,"value",void 0),e([pe({type:Boolean})],Fi.prototype,"disabled",void 0),e([pe({attribute:!1})],Fi.prototype,"excludeEntityIds",void 0),e([ge()],Fi.prototype,"_didAutoSelect",void 0),e([ge()],Fi.prototype,"_receiverIds",void 0),Fi=e([ue("ir-emitter-picker")],Fi);const Wi=[3e4,33e3,36e3,38e3,4e4,56e3],Gi=e=>Wi.reduce((t,i)=>Math.abs(i-e)<Math.abs(t-e)?i:t);let Zi=class extends se{constructor(){super(...arguments),this.signalId=null,this.commandId=null,this.initialPronto="",this.initialAlias="",this.initialSendCount=1,this.initialDitto=1,this.initialObservedRepeatCount=0,this.initialTxForceRaw=!1,this.initialDecodedProtocol=null,this.hasTrigger=!1,this.allowSnap=!1,this._pronto="",this._alias="",this._sendCount=1,this._ditto=1,this._busy=!1,this._error=null,this._validation=null,this._copyHint=null,this._snapping=!1,this._snapFlash=!1,this._debounce=null}get _isCommand(){return null!==this.commandId}get _isEdit(){return null!==this.signalId||null!==this.commandId}get _dirty(){return this._pronto!==this.initialPronto||this._alias!==this.initialAlias||this._sendCount!==this.initialSendCount||this._ditto!==this.initialDitto}get _canSave(){return!this._busy&&!0===this._validation?.valid&&(!this._isEdit||this._dirty)}get _dittoCountDisabled(){return this._isCommand?!this.initialDecodedProtocol||!!this.initialTxForceRaw:!this._pronto.trim()||null===this._validation||!this._validation.recognized_protocol}get _dittoDisabledTooltip(){return this._isCommand&&this.initialDecodedProtocol&&this.initialTxForceRaw?ke("editor.ditto_disabled_cmd"):ke("editor.ditto_disabled")}firstUpdated(){this._pronto=this.initialPronto,this._alias=this.initialAlias,this._sendCount=this.initialSendCount,this._ditto=this.initialDitto,this._pronto.trim()&&this._validate()}updated(){const e=this.shadowRoot?.querySelector("textarea");if(!e)return;const t=Math.round(.45*window.innerHeight);e.style.height="0px";const i=Math.min(Math.max(e.scrollHeight+2,64),t);e.style.height=`${i}px`}disconnectedCallback(){super.disconnectedCallback(),null!==this._debounce&&clearTimeout(this._debounce)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._ditto=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}_onProntoInput(e){this._pronto=e.target.value,null!==this._debounce&&clearTimeout(this._debounce),this._pronto.trim()?this._debounce=setTimeout(()=>{this._validate()},250):this._validation=null}_onKeydown(e){"Enter"!==e.key||e.shiftKey||(e.preventDefault(),this._canSave&&this._save())}async _validate(){try{this._validation=await this.api.validatePronto(this._pronto)}catch{this._validation=null}}_slPreview(){const e=this._validation?.normalized;if(!e)return null;const t=e.split(" ").map(e=>parseInt(e,16));if(t.length<5||t.some(e=>Number.isNaN(e)))return null;const i=[];for(const e of t.slice(4)){if(e>=1024)break;i.push(e<48?"S":"L")}return i.length?i:null}async _save(){if(!this._canSave)return;this._busy=!0,this._error=null;const e=this._dittoCountDisabled?void 0:this._ditto;try{if(this._isCommand){const t=await this.api.updateCommand({device_id:this.deviceId,command_id:this.commandId,name:this._alias.trim(),pronto:this._pronto,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("command-edited",{detail:t,bubbles:!0,composed:!0}))}else if(null!==this.signalId){const t=await this.api.editSignalPronto({device_id:this.deviceId,signal_id:this.signalId,pronto:this._pronto,alias:this._alias.trim(),send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-edited",{detail:t,bubbles:!0,composed:!0}))}else{const t=await this.api.createSignal({device_id:this.deviceId,pronto:this._pronto,alias:this._alias.trim()||void 0,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-created",{detail:t.signal,bubbles:!0,composed:!0}))}}catch(e){this._error=e.message}finally{this._busy=!1}}async _selectCode(){const e=this.shadowRoot?.querySelector("textarea");e&&(e.focus(),e.select());let t=!1;try{window.isSecureContext&&navigator.clipboard&&(await navigator.clipboard.writeText(this._pronto),t=!0)}catch{t=!1}this._copyHint=ke(t?"editor.copied":"editor.press_copy"),setTimeout(()=>{this._copyHint=null},2e3)}_renderFeedback(){const e=this._validation;if(!e)return"";const t=this._slPreview();return B`
            <div class="feedback">
                <div class="status ${e.valid?"ok":"bad"}">
                    <span class="mark">${e.valid?"✓":"✗"}</span>
                    ${e.valid?ke("editor.valid"):ke("editor.not_valid")}
                </div>
                ${e.valid?B`
                          <div class="metrics">
                              ${null!==e.frequency_khz?B`<span>${e.frequency_khz} kHz</span>`:""}
                              ${null!==e.burst_pair_count?B`<span
                                        >${$e("editor.burst_pair",e.burst_pair_count)}</span
                                    >`:""}
                              ${e.recognized_protocol?B`<span class="recognized"
                                        >${ke("editor.recognized_as",{protocol:e.recognized_protocol})}</span
                                    >`:""}
                          </div>
                          ${t?B`<div class="diamonds">
                                    ${t.map(e=>"L"===e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}
                                </div>`:""}
                      `:""}
                ${e.errors.map(e=>B`<div class="msg err">${e}</div>`)}
                ${e.warnings.map(e=>B`<div class="msg warn">${e}</div>`)}
            </div>
        `}get _carrierHz(){const e=this._validation?.valid?this._validation.frequency_khz:null;return null!=e?Math.round(1e3*e):null}get _showSnap(){if(!this.allowSnap)return!1;const e=this._carrierHz;return null!=e&&!(e=>Math.abs(e-Gi(e))<=500)(e)}async _snap(e){this._snapping=!0,this._error=null;try{const t=await this.api.snapPreview({pronto:this._pronto,target_frequency:e});this._pronto=t.pronto,await this._validate(),this._snapFlash=!0,setTimeout(()=>{this._snapFlash=!1},700)}catch(e){this._error=e.message}finally{this._snapping=!1}}_renderSnap(){if(!this._showSnap)return"";const e=this._carrierHz,t=Gi(e),i=(e/1e3).toFixed(1),a=(t/1e3).toFixed(0);return B`
            <div class="snap-notice">
                <div class="snap-text">
                    ${ke("editor.snap_notice",{khz:i})}
                </div>
                <button
                    class="snap-btn"
                    ?disabled=${this._snapping}
                    @click=${()=>this._snap(t)}
                >
                    ${this._snapping?ke("editor.snapping"):ke("editor.snap_to",{khz:a})}
                </button>
            </div>
        `}render(){const e=this._isCommand?ke("editor.edit_command"):this._isEdit?ke("editor.edit_signal"):ke("editor.create_signal"),t=this._isEdit?this._busy?ke("common.saving"):ke("common.save"):this._busy?ke("common.creating"):ke("common.create"),i=this._isEdit&&this.hasTrigger&&this._dirty,a=this._isCommand?ke("editor.trigger_note_cmd"):ke("editor.trigger_note_sig"),r=this._isCommand?ke("assign.command_name"):this._isEdit?ke("editor.alias_label"):ke("editor.alias_optional");return B`
            <ha-dialog
                open
                heading=${e}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${ke("editor.pronto_code")}</label>
                    <div class="code-wrap">
                        <textarea
                            class=${this._snapFlash?"snap-flash":""}
                            rows="4"
                            .value=${this._pronto}
                            placeholder="0000 006D ..."
                            autofocus
                            spellcheck="false"
                            @input=${this._onProntoInput}
                            @keydown=${this._onKeydown}
                        ></textarea>
                        ${this._pronto.trim()?B`
                                  ${this._copyHint?B`<span class="copy-flash"
                                            >${this._copyHint}</span
                                        >`:""}
                                  <button
                                      class="copy-icon"
                                      title=${ke("editor.select_all")}
                                      @click=${this._selectCode}
                                  >
                                      <ha-svg-icon
                                          .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                      ></ha-svg-icon>
                                  </button>
                              `:""}
                    </div>
                </div>

                ${this._renderFeedback()} ${this._renderSnap()}

                <div class="field">
                    <label>${r}</label>
                    <input
                        type="text"
                        .value=${this._alias}
                        placeholder=${ke("editor.alias_placeholder")}
                        @input=${e=>this._alias=e.target.value}
                        @keydown=${this._onKeydown}
                    />
                </div>

                <div class="field tx-knobs">
                    <div class="knob">
                        <label>${ke("assign.send_times")}</label>
                        <input
                            class="num-input"
                            type="number"
                            min="1"
                            max="10"
                            .value=${String(this._sendCount)}
                            title=${ke("editor.send_times_title")}
                            @input=${this._onSendCountInput}
                            @keydown=${this._onKeydown}
                        />
                    </div>
                    ${this._dittoCountDisabled?"":B`<div class="knob">
                              <label>${ke("assign.ditto_count")}</label>
                              <input
                                  class="num-input"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._ditto)}
                                  title=${ke("editor.ditto_title")}
                                  @input=${this._onDittoInput}
                                  @keydown=${this._onKeydown}
                              />
                          </div>`}
                </div>
                ${this.initialObservedRepeatCount>0?B`<div class="observed-hint">
                          ${$e("editor.observed",this.initialObservedRepeatCount)}
                      </div>`:""}

                ${i?B`<div class="note">${a}</div>`:""}

                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._save}
                        ?disabled=${!this._canSave}
                    >
                        ${t}
                    </button>
                </div>
            </ha-dialog>
        `}};Zi.styles=[Bi,n`
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        input[type="text"],
        textarea {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            font-family: monospace;
            resize: vertical;
            /* Extra top padding keeps the first line of code clear of the
               corner copy icon. */
            padding-top: 24px;
            /* updated() sizes the height to fit the code (clamped in JS), so
               a long Pronto scrolls instead of overflowing the dialog. */
            overflow-y: auto;
        }
        .code-wrap {
            position: relative;
        }
        .copy-icon {
            position: absolute;
            top: 6px;
            right: 8px;
            z-index: 2;
            display: inline-flex;
            align-items: center;
            padding: 2px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.55;
            transition: opacity 150ms ease;
        }
        .copy-icon:hover {
            opacity: 0.9;
        }
        .copy-icon ha-svg-icon {
            --mdc-icon-size: 12px;
        }
        .copy-flash {
            position: absolute;
            top: 7px;
            right: 34px;
            z-index: 2;
            font-size: 0.72rem;
            white-space: nowrap;
            color: var(--secondary-text-color);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 1px 6px;
            pointer-events: none;
        }
        input[type="text"]:focus,
        textarea:focus {
            outline: none;
            border-color: #b87333;
        }
        .tx-knobs {
            display: flex;
            gap: 16px;
        }
        .knob {
            display: flex;
            flex-direction: column;
        }
        input.num-input {
            width: 80px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input.num-input:focus {
            outline: none;
            border-color: #b87333;
        }
        input.num-input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .observed-hint {
            margin: -4px 0 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        .hint {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        @keyframes snap-flash {
            0% {
                border-color: #ff9800;
                background: rgba(255, 152, 0, 0.18);
            }
            100% {
                border-color: var(--divider-color);
                background: var(--card-background-color);
            }
        }
        textarea.snap-flash {
            animation: snap-flash 700ms ease-out;
        }
        .snap-notice {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border: 1px solid rgba(255, 152, 0, 0.35);
        }
        .snap-text {
            flex: 1;
            font-size: 0.8rem;
            line-height: 1.3;
            color: #b26500;
        }
        .snap-btn {
            flex-shrink: 0;
            background: none;
            border: 1px solid #e65100;
            color: #e65100;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 0.8rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .snap-btn:hover:not(:disabled) {
            background: rgba(255, 152, 0, 0.12);
        }
        .snap-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .feedback {
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: var(--secondary-background-color);
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .status .mark {
            font-size: 1rem;
        }
        .status.ok {
            color: #2e7d32;
        }
        .status.bad {
            color: #e65100;
        }
        .metrics {
            display: flex;
            gap: 14px;
            margin-top: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
        .recognized {
            color: #2e7d32;
        }
        .diamonds {
            display: flex;
            flex-wrap: wrap;
            gap: 1px;
            margin-top: 8px;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .msg {
            margin-top: 6px;
            font-size: 0.8rem;
        }
        .msg.err {
            color: #e65100;
        }
        .msg.warn {
            color: #b89930;
        }
        .note {
            margin: 4px 0 12px;
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
        }
        /* Left-aligned actions row (a spacer pushes the main buttons
           right so Delete can sit flush left); ships this way. */
        .dialog-actions {
            align-items: center;
            justify-content: flex-start;
        }
        .spacer {
            flex: 1;
        }
        .copy-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .copy-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],Zi.prototype,"api",void 0),e([pe({attribute:!1})],Zi.prototype,"deviceId",void 0),e([pe({attribute:!1})],Zi.prototype,"signalId",void 0),e([pe({attribute:!1})],Zi.prototype,"commandId",void 0),e([pe({attribute:!1})],Zi.prototype,"initialPronto",void 0),e([pe({attribute:!1})],Zi.prototype,"initialAlias",void 0),e([pe({attribute:!1})],Zi.prototype,"initialSendCount",void 0),e([pe({attribute:!1})],Zi.prototype,"initialDitto",void 0),e([pe({attribute:!1})],Zi.prototype,"initialObservedRepeatCount",void 0),e([pe({attribute:!1})],Zi.prototype,"initialTxForceRaw",void 0),e([pe({attribute:!1})],Zi.prototype,"initialDecodedProtocol",void 0),e([pe({type:Boolean})],Zi.prototype,"hasTrigger",void 0),e([pe({type:Boolean})],Zi.prototype,"allowSnap",void 0),e([ge()],Zi.prototype,"_pronto",void 0),e([ge()],Zi.prototype,"_alias",void 0),e([ge()],Zi.prototype,"_sendCount",void 0),e([ge()],Zi.prototype,"_ditto",void 0),e([ge()],Zi.prototype,"_busy",void 0),e([ge()],Zi.prototype,"_error",void 0),e([ge()],Zi.prototype,"_validation",void 0),e([ge()],Zi.prototype,"_copyHint",void 0),e([ge()],Zi.prototype,"_snapping",void 0),e([ge()],Zi.prototype,"_snapFlash",void 0),Zi=e([ue("ir-signal-editor")],Zi);let Ki=class extends se{constructor(){super(...arguments),this.value=[],this.disabled=!1,this._receivers=[],this._receiversLoaded=!1}updated(e){super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers())}async _loadReceivers(){if(this.api)try{this._receivers=await this.api.listReceivers()}catch{this._receivers=[]}}_receiverName(e){const t=this._receivers.find(t=>t.entity_id===e);return t?.name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("receivers-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._receivers.filter(e=>!this.value.includes(e.entity_id));return B`
            <label>${ke("picker.receivers_label")}</label>

            ${this.value.length>0?B`
                      <div class="chips">
                          ${this.value.map(e=>B`
                                  <span class="chip">
                                      <span class="chip-name"
                                          >${this._receiverName(e)}</span
                                      >
                                      ${this.disabled?"":B`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title=${ke("common.remove")}
                                            >
                                                &times;
                                            </button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===this._receivers.length?B`<div class="no-receivers">${ke("picker.no_receivers")}</div>`:e.length>0?B`
                        <select @change=${this._onAdd} ?disabled=${this.disabled}>
                            <option value="">${ke("picker.add_receiver")}</option>
                            ${e.map(e=>B`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:B`<div class="all-selected">${ke("picker.all_receivers_selected")}</div>`}
        `}};Ki.styles=n`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 6px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--secondary-background-color);
            color: var(--primary-color);
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
            line-height: 1;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chip-remove {
            background: none;
            border: none;
            color: inherit;
            font-size: 1rem;
            cursor: pointer;
            padding: 0 2px;
            line-height: 1;
            opacity: 0.65;
            transition: opacity 120ms ease;
        }
        .chip-remove:hover {
            opacity: 1;
        }
        select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-receivers,
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,e([pe({attribute:!1})],Ki.prototype,"api",void 0),e([pe({attribute:!1})],Ki.prototype,"value",void 0),e([pe({type:Boolean})],Ki.prototype,"disabled",void 0),e([ge()],Ki.prototype,"_receivers",void 0),Ki=e([ue("ir-receiver-picker")],Ki);let Xi=class extends se{constructor(){super(...arguments),this.signalFingerprint="",this.protocol=null,this.code=null,this.slPattern=null,this.alias=null,this.byteHash=null,this.decodedFingerprint=null,this.sourceDeviceId=null,this.sourceCommandId=null,this.trigger=null,this.mirrorContext=!1,this._name="",this._minHits=1,this._receiverIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.trigger&&(this._name=this.trigger.name,this._minHits=this.trigger.min_hits,this._receiverIds=[...this.trigger.receiver_entity_ids??[]])}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _save(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{let t;if(this.trigger)t=await this.api.updateTrigger(this.trigger.id,{name:e,min_hits:this._minHits,receiver_entity_ids:this._receiverIds});else{const i={name:e,protocol:this.protocol,code:this.code,min_hits:this._minHits,source_device_id:this.sourceDeviceId,source_command_id:this.sourceCommandId,receiver_entity_ids:this._receiverIds};this.signalFingerprint&&(i.signal_fingerprint=this.signalFingerprint),this.byteHash&&(i.byte_hash=this.byteHash),this.decodedFingerprint&&(i.decoded_fingerprint=this.decodedFingerprint),t=await this.api.createTrigger(i)}this.dispatchEvent(new CustomEvent("trigger-saved",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message??ke("trigger.save_failed")}finally{this._busy=!1}}else this._error=ke("common.name_required")}_emitDelete(){this.trigger&&this.dispatchEvent(new CustomEvent("trigger-delete",{detail:{triggerId:this.trigger.id},bubbles:!0,composed:!0}))}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),a=t.slice(4);if(a.length<2*i)return null;const r=[];for(let e=0;e<2*i;e++){const t=parseInt(a[e],16);r.push(t>=48)}return r.length>0?r:null}_renderSignalInfo(){const e=!!this.trigger;if(!e&&this.alias)return B`<span class="alias-inline"
                ><span class="alias-tag">${ke("trigger.alias_tag")}</span
                ><span class="alias-name">${this.alias}</span></span
            >`;const t=e?null:this.slPattern;if(t)return B`<span class="diamonds">${[...t].map(e=>"L"===e?B`<span class="diamond long">&#9670;</span>`:B`<span class="diamond short">&#9671;</span>`)}</span>`;const i=e?this.trigger.code:this.code,a=e?this.trigger.protocol:this.protocol;if("PRONTO"===a?.toUpperCase()&&i){const e=this._prontoSlArray(i);if(e)return B`<span class="diamonds">${e.map(e=>e?B`<span class="diamond long">&#9670;</span>`:B`<span class="diamond short">&#9671;</span>`)}</span>`}return B`<span class="proto">${ke("trigger.event")}</span>`}render(){const e=!!this.trigger;return B`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">
                        ${ke(e?"trigger.edit_heading":"trigger.create_heading")}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    ${this.mirrorContext?B`<p class="field-hint scope-hint">
                              ${ke("trigger.mirror_hint")}
                          </p>`:""}

                    <!-- Name -->
                    <label class="field-label">${ke("trigger.name_label")}</label>
                    <input
                        class="field-input"
                        type="text"
                        placeholder=${ke("trigger.name_placeholder")}
                        .value=${this._name}
                        @input=${e=>{this._name=e.target.value}}
                        ?disabled=${this._busy}
                    />

                    <!-- Min Hits -->
                    <label class="field-label">
                        ${ke("trigger.min_hits")}
                        <span class="field-hint">
                            ${ke("trigger.min_hits_hint")}
                        </span>
                    </label>
                    <input
                        class="field-input hits-input"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._minHits)}
                        @input=${e=>{const t=parseInt(e.target.value,10);t>=1&&t<=10&&(this._minHits=t)}}
                        ?disabled=${this._busy}
                    />

                    <!-- Receiver scope -->
                    <div class="receiver-field">
                        <ir-receiver-picker
                            .api=${this.api}
                            .value=${this._receiverIds}
                            ?disabled=${this._busy}
                            @receivers-changed=${e=>{this._receiverIds=e.detail.value}}
                        ></ir-receiver-picker>
                        <p class="field-hint scope-hint">
                            ${ke("trigger.scope_hint")}
                        </p>
                    </div>

                    ${this._error?B`<p class="error">${this._error}</p>`:""}

                    <div class="actions">
                        ${e?B`<button
                                  class="btn delete-btn"
                                  @click=${this._emitDelete}
                                  ?disabled=${this._busy}
                              >${ke("common.delete")}</button>`:""}
                        <span class="actions-spacer"></span>
                        <button
                            class="btn cancel"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >${ke("common.cancel")}</button>
                        <button
                            class="btn save"
                            @click=${this._save}
                            ?disabled=${this._busy||!this._name.trim()}
                        >${this._busy?ke("common.saving"):ke(e?"common.update":"common.create")}</button>
                    </div>
                </div>
            </div>
        `}};Xi.styles=[Bi,n`
        .signal-info {
            padding: 8px 12px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            margin-bottom: 16px;
            font-family: var(--code-font-family, monospace);
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .proto {
            text-transform: uppercase;
            font-weight: 500;
        }
        .alias-inline {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
        }
        .alias-tag {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .field-label {
            display: block;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 4px;
        }
        .field-hint {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.78rem;
            margin-left: 4px;
        }
        .field-input {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            margin-bottom: 14px;
            outline: none;
            transition: border-color 150ms ease;
        }
        .field-input:focus {
            border-color: var(--primary-color);
        }
        .field-input:disabled {
            opacity: 0.5;
        }
        .hits-input {
            width: 80px;
        }
        .receiver-field {
            margin-bottom: 14px;
        }
        .scope-hint {
            margin: 6px 0 0;
            margin-left: 0;
        }
        .error {
            color: #e65100;
            font-size: 0.85rem;
            margin: 0 0 12px;
        }
        .actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
        }
        .actions-spacer {
            flex: 1;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        .save {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .save:hover {
            background: #a08328;
        }
        .delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.3);
        }
        .delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
    `],e([pe({attribute:!1})],Xi.prototype,"api",void 0),e([pe()],Xi.prototype,"signalFingerprint",void 0),e([pe()],Xi.prototype,"protocol",void 0),e([pe()],Xi.prototype,"code",void 0),e([pe()],Xi.prototype,"slPattern",void 0),e([pe()],Xi.prototype,"alias",void 0),e([pe()],Xi.prototype,"byteHash",void 0),e([pe()],Xi.prototype,"decodedFingerprint",void 0),e([pe()],Xi.prototype,"sourceDeviceId",void 0),e([pe()],Xi.prototype,"sourceCommandId",void 0),e([pe({attribute:!1})],Xi.prototype,"trigger",void 0),e([pe({type:Boolean})],Xi.prototype,"mirrorContext",void 0),e([ge()],Xi.prototype,"_name",void 0),e([ge()],Xi.prototype,"_minHits",void 0),e([ge()],Xi.prototype,"_receiverIds",void 0),e([ge()],Xi.prototype,"_busy",void 0),e([ge()],Xi.prototype,"_error",void 0),Xi=e([ue("ir-trigger-dialog")],Xi);const Yi=n`
    .action-popover {
        position: fixed;
        z-index: 50;
        min-width: 200px;
        max-width: 280px;
        background: var(--card-background-color, #1c1c1c);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        padding: 4px 0;
        overflow: auto;
        max-height: 320px;
    }
    .popover-header {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--secondary-text-color);
        padding: 6px 12px 4px;
    }
    .popover-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 7px 12px;
        background: none;
        border: none;
        color: var(--primary-text-color);
        font-size: 0.82rem;
        font-family: inherit;
        cursor: pointer;
        text-align: left;
        transition: background 100ms ease;
    }
    .popover-item:hover {
        background: var(--secondary-background-color);
    }
    .popover-item.active {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-item.clear {
        color: var(--secondary-text-color);
        font-style: italic;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 2px;
    }
    .popover-check {
        color: var(--primary-color);
        font-size: 0.9rem;
    }
    .popover-existing {
        font-size: 0.72rem;
        color: var(--secondary-text-color);
        font-style: italic;
        margin-left: 8px;
        flex-shrink: 0;
    }
    /* Trigger-popover extras (v0.5.7) */
    .popover-item.accent {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-divider {
        height: 1px;
        background: var(--divider-color);
        margin: 2px 0;
    }
    .popover-row {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 2px;
        min-width: 0;
    }
    .popover-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 240px;
    }
    .popover-scope {
        font-size: 0.7rem;
        color: var(--secondary-text-color);
    }
`;let Qi=class extends se{constructor(){super(...arguments),this.triggers=[],this.receivers=[],this.top=0,this.left=0}render(){return B`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${ke("popover.triggers")}</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>${ke("popover.new_trigger")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.triggers.map(e=>B`
                        <button
                            class="popover-item"
                            @click=${()=>this._emit("edit-trigger",e)}
                        >
                            <span class="popover-row">
                                <span class="popover-name">${e.name}</span>
                                <span class="popover-scope"
                                    >${this._renderScope(e)}</span
                                >
                            </span>
                        </button>
                    `)}
            </div>
        `}_renderScope(e){const t=e.receiver_entity_ids??[];return 0===t.length?ke("popover.any_receiver"):1===t.length?this._friendly(t[0]):ke("popover.n_more",{name:this._friendly(t[0]),count:t.length-1})}_friendly(e){const t=this.receivers.find(t=>t.entity_id===e);return t?.name??e}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};Qi.styles=[Yi,n`
            :host {
                display: contents;
            }
        `],e([pe({attribute:!1})],Qi.prototype,"triggers",void 0),e([pe({attribute:!1})],Qi.prototype,"receivers",void 0),e([pe({type:Number})],Qi.prototype,"top",void 0),e([pe({type:Number})],Qi.prototype,"left",void 0),Qi=e([ue("ir-trigger-popover")],Qi);const Ji=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let ea=class extends se{constructor(){super(...arguments),this._busy=!1,this._captureName=null,this._toast=null,this._confirmDelete=!1,this._commandToDelete=null,this._editCommand=null,this._actionOptions=[],this._mappingCommandName=null,this._popoverTop=0,this._popoverLeft=0,this._customActionOpen=!1,this._customActionValue="",this._dismissHandler=null,this._editingName=!1,this._draftName="",this._triggers=[],this._triggerCommand=null,this._triggerEdit=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._receivers=[],this._sortable=null,this._pendingReorderTimeout=null,this._commandsListVersion=0,this._onDocClickForTriggerPopover=e=>{const t=this.shadowRoot?.querySelector("ir-trigger-popover");t&&e.composedPath().includes(t)||this._closeTriggerPopover()},this._onScrollForTriggerPopover=()=>{this._closeTriggerPopover()}}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_deviceRegistryName(e){const t=this.hass?.devices?.[e];return t?.name_by_user??t?.name??e}_deviceConfigEntryId(e){const t=this.hass?.devices?.[e];return t?(t.config_entries??[])[0]??null:null}_configEntryDomain(e){const t=this.hass?.config_entries?.entries?.[e];return t?.domain??null}_integrationUrl(e){if(!e)return null;const t=this._configEntryDomain(e);return t?`/config/integrations/integration/${t}`:null}_entityIntegrationUrl(e){const t=e.split(".")[0],i=this.hass?.entities?.[e];return i?.config_entry_id?this._integrationUrl(i.config_entry_id):i?.platform?`/config/integrations/integration/${i.platform}`:`/config/integrations/integration/${t}`}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}_startEditName(){this._draftName=this.device.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()})}async _saveName(){const e=this._draftName.trim();if(e&&e!==this.device.name){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{name:e}),this._flash(ke("devdetail.name_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1,this._editingName=!1}}else this._editingName=!1}_onNameKeyDown(e){"Enter"===e.key?(e.preventDefault(),this._saveName()):"Escape"===e.key&&(this._editingName=!1)}async _onTypeChanged(e){const t=e.target.value;if(t!==this.device.device_type){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{device_type:t}),this._flash(ke("devdetail.type_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}}async _onEmittersChanged(e){const t=e.detail.value,i=[...this.device.emitter_entity_ids];this.device={...this.device,emitter_entity_ids:t},this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{emitter_entity_ids:t}),this._flash(ke("devdetail.emitters_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this.device={...this.device,emitter_entity_ids:i},this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}connectedCallback(){super.connectedCallback(),this._loadActionOptions(),this._loadTriggers(),this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}updated(e){e.has("device")&&(this._loadActionOptions(),this._loadTriggers()),e.has("_commandsListVersion")&&!this._sortable&&this._attachSortable()}async _loadActionOptions(){try{this._actionOptions=await this.api.getActionOptions(this.device.device_type)}catch{this._actionOptions=[]}}async _loadTriggers(){try{this._triggers=await this.api.listTriggers()}catch{this._triggers=[]}}_commandHasTrigger(e){return this._triggers.some(t=>t.source_command_id===e.id)}_commandTriggerCount(e){return this._triggers.filter(t=>t.source_command_id===e.id).length}_onToggleTrigger(e){const t=e.detail?.command;if(!t)return;const i=this._triggers.filter(e=>e.source_command_id===t.id);if(0===i.length)return void(this._triggerCommand=t);const a=e.detail?.buttonRect;this._triggerPopover={command:t,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installTriggerPopoverDismiss()}_triggersForCommand(e){return this._triggers.filter(t=>t.source_command_id===e.id)}_closeTriggerPopover(){this._triggerPopover=null,this._removeTriggerPopoverDismiss()}_onTriggerPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerCommand=e.command)}_onTriggerPopoverEdit(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEdit=t)}_installTriggerPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForTriggerPopover,!0),window.addEventListener("scroll",this._onScrollForTriggerPopover,!0)},0)}_removeTriggerPopoverDismiss(){document.removeEventListener("click",this._onDocClickForTriggerPopover,!0),window.removeEventListener("scroll",this._onScrollForTriggerPopover,!0)}_closeTriggerDialog(){this._triggerCommand=null,this._triggerEdit=null}async _onTriggerSaved(){this._triggerCommand=null,this._triggerEdit=null,await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEdit=null;try{await this.api.deleteTrigger(e),await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}catch{}}_getActionLabel(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,a]of Object.entries(t))if(a.toLowerCase()===e.toLowerCase()){const e=this._actionOptions.find(e=>e.key===i);return e?xe(e.label):i}return null}_onMapAction(e){const{command:t}=e.detail;if(!t)return;const i=e.target.shadowRoot?.querySelector(".badge-btn");if(i){const e=i.getBoundingClientRect();this._popoverTop=e.bottom+4,this._popoverLeft=Math.max(8,e.right-220)}this._mappingCommandName=t.name,requestAnimationFrame(()=>{this._dismissHandler=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector(".action-popover");i&&!t.includes(i)&&this._closePopover()},document.addEventListener("click",this._dismissHandler,!0)})}_closePopover(){this._mappingCommandName=null,this._customActionOpen=!1,this._customActionValue="",this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null)}disconnectedCallback(){super.disconnectedCallback(),this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null),this._removeTriggerPopoverDismiss(),this._sortable?.destroy(),this._sortable=null,this._cancelPendingReorderSave()}firstUpdated(){this._attachSortable()}_attachSortable(){if(this._sortable)return;const e=this.renderRoot.querySelector(".commands-list");e&&(this._sortable=bi.create(e,{handle:".grip-handle",animation:150,ghostClass:"sortable-ghost",onEnd:e=>{const t=e.oldIndex,i=e.newIndex;if(void 0===t||void 0===i||t===i)return;const a=[...this.device.commands],[r]=a.splice(t,1);a.splice(i,0,r),this.device={...this.device,commands:a},this.dispatchEvent(new CustomEvent("commands-reordered",{detail:{commands:a},bubbles:!0,composed:!0})),this._sortable?.destroy(),this._sortable=null;const o=this.renderRoot.querySelector(".commands-list");if(o)for(const e of Array.from(o.querySelectorAll("ir-command-row")))e.remove();this._commandsListVersion++,this._scheduleReorderSave(a.map(e=>e.id))}}))}_scheduleReorderSave(e){this._cancelPendingReorderSave(),this._pendingReorderTimeout=window.setTimeout(async()=>{this._pendingReorderTimeout=null;try{await this.api.reorderCommands(this.device.id,e)}catch(e){this._flash(ke("devdetail.reorder_failed",{message:e.message})),await this._refresh()}},500)}_cancelPendingReorderSave(){null!==this._pendingReorderTimeout&&(clearTimeout(this._pendingReorderTimeout),this._pendingReorderTimeout=null)}_getCommandForAction(e){return(this.device.entity_config?.command_mapping??{})[e]??null}async _selectAction(e,t){this._closePopover(),this._busy=!0;try{const i=await this.api.updateMapping(this.device.id,e,t);this.device={...this.device,entity_config:{...this.device.entity_config,command_mapping:i.mapping}},this._flash(t?ke("devdetail.mapped_to",{action:t}):ke("devdetail.mapping_cleared")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(ke("devdetail.mapping_failed",{message:e.message}))}finally{this._busy=!1}}_getCurrentActionKey(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,a]of Object.entries(t))if(a.toLowerCase()===e.toLowerCase())return i;return""}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash(ke("devdetail.sent_cmd",{name:t.name}))}catch(e){this._flash(ke("devdetail.send_failed",{message:e.message}))}finally{this._busy=!1}}}async _onToggleTxRaw(e){const{command:t}=e.detail;if(!t)return;const i=!t.tx_force_raw;this._busy=!0;try{await this.api.setCommandTxForceRaw(this.device.id,t.id,i),t.tx_force_raw=i,this.requestUpdate(),this._flash(i?`"${t.name}" will transmit the captured timings`:`"${t.name}" will transmit clean decoded timings`)}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}_onDelete(e){const{command:t}=e.detail;t&&(this._commandToDelete=t)}_onEditCommand(e){const{command:t}=e.detail;t&&(this._editCommand=t)}async _onCommandEdited(e){const t=e.detail;this._editCommand=null,await this._refresh();const i=t.triggers?.rewired??[];if(i.length){const e=i.map(e=>`"${e}"`).join(", ");this._flash(ke("devdetail.cmd_updated_repointed",{names:e}))}else this._flash(ke("devdetail.cmd_updated"));this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}async _onRenameCommand(e){const{command:t,name:i}=e.detail;this._busy=!0;try{const e=await this.api.updateCommand({device_id:this.device.id,command_id:t.id,name:i});await this._refresh();const a=e.mappings_updated;this._flash(a>0?`Renamed (updated ${a} action mapping${1===a?"":"s"})`:"Renamed"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(ke("devdetail.rename_failed",{message:e.message}))}finally{this._busy=!1}}async _confirmCommandDelete(){const e=this._commandToDelete;if(e){this._commandToDelete=null,this._cancelPendingReorderSave(),this._busy=!0;try{await this.api.deleteCommand(this.device.id,e.id),await this._refresh(),this._flash(ke("devdetail.removed",{name:e.name}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null}async _onCommandSaved(e){const{commandName:t}=e.detail;this._cancelPendingReorderSave(),await this._refresh(),this._flash(ke("devdetail.saved",{name:t})),this._captureName=null}_goToSniffer(){this.dispatchEvent(new CustomEvent("navigate-sniffer",{bubbles:!0,composed:!0}))}_goToClips(){this.dispatchEvent(new CustomEvent("navigate-clips",{bubbles:!0,composed:!0}))}_goToMirror(){this.dispatchEvent(new CustomEvent("navigate-mirror",{bubbles:!0,composed:!0}))}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}_navigateIntegration(e){e&&(window.history.pushState(null,"",e),window.dispatchEvent(new PopStateEvent("popstate")))}render(){const e=this.device.commands,t=e.length;return B`
            <!-- Header: editable name + delete -->
            <section class="header">
                <div class="header-left">
                    ${this._editingName?B`
                              <input
                                  class="name-input"
                                  type="text"
                                  .value=${this._draftName}
                                  @input=${e=>this._draftName=e.target.value}
                                  @blur=${this._saveName}
                                  @keydown=${this._onNameKeyDown}
                                  ?disabled=${this._busy}
                              />
                          `:B`
                              <h1
                                  class="editable-name"
                                  @click=${this._startEditName}
                                  title=${ke("cmdrow.rename")}
                              >
                                  ${this.device.name}
                                  <span class="edit-icon">&#9998;</span>
                              </h1>
                          `}
                </div>
                <button
                    class="action-btn collapse-btn"
                    @click=${()=>this.dispatchEvent(new CustomEvent("collapse",{bubbles:!0,composed:!0}))}
                    title=${ke("common.close")}
                >&#x2715;</button>
            </section>

            <!-- Device metadata grid -->
            <div class="device-meta">
                <span class="meta-label">${ke("devdetail.type")}</span>
                <div class="meta-value">
                    <select
                        .value=${this.device.device_type}
                        @change=${this._onTypeChanged}
                        ?disabled=${this._busy}
                    >
                        ${Ji.map(e=>B`
                                <option
                                    value=${e.value}
                                    ?selected=${this.device.device_type===e.value}
                                >
                                    ${ke(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>
                <span class="meta-label">${ke("devlist.emitters")}</span>
                <div class="meta-value">
                    <ir-emitter-picker
                        .hass=${this.hass}
                        .api=${this.api}
                        .value=${this.device.emitter_entity_ids??[]}
                        ?disabled=${this._busy}
                        @emitters-changed=${this._onEmittersChanged}
                    ></ir-emitter-picker>
                </div>
            </div>

            <!-- Commands -->
            <div class="commands-section">
                <div class="commands-header">
                    <span>${ke("devdetail.commands",{count:t})}</span>
                </div>
                <div class="commands-list">
                    ${He(this._commandsListVersion,e.length>0?Me(e,e=>e.id,e=>B`
                                      <ir-command-row
                                          data-id=${e.id}
                                          .templateName=${e.name}
                                          .command=${e}
                                          .busy=${this._busy}
                                          .actionLabel=${this._getActionLabel(e.name)}
                                          .hasTrigger=${this._commandHasTrigger(e)}
                                          .triggerCount=${this._commandTriggerCount(e)}
                                          .showActionMapping=${"other"!==this.device.device_type}
                                          @map-action=${this._onMapAction}
                                          @test=${this._onTest}
                                          @toggle-trigger=${this._onToggleTrigger}
                                          @toggle-tx-raw=${this._onToggleTxRaw}
                                          @edit-command=${this._onEditCommand}
                                          @rename-command=${this._onRenameCommand}
                                          @delete=${this._onDelete}
                                      >
                                          <ha-svg-icon
                                              slot="status"
                                              class="grip-handle"
                                              .path=${"M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z"}
                                              title=${ke("devdetail.drag")}
                                          ></ha-svg-icon>
                                      </ir-command-row>
                                  `):B`<div class="empty">${ke("devdetail.no_commands")}</div>`)}

                    ${this._mappingCommandName?B`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">${ke("devdetail.map_action")}</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)?B`
                                            <button
                                                class="popover-item clear"
                                                @click=${()=>this._selectAction(this._mappingCommandName,null)}
                                            >
                                                <span class="popover-label">${ke("devdetail.none_clear")}</span>
                                            </button>
                                        `:""}
                                  ${this._actionOptions.map(e=>{const t=this._getCurrentActionKey(this._mappingCommandName)===e.key,i=this._getCommandForAction(e.key),a=i&&i.toLowerCase()!==this._mappingCommandName.toLowerCase();return B`
                                          <button
                                              class="popover-item ${t?"active":""}"
                                              @click=${()=>this._selectAction(this._mappingCommandName,e.key)}
                                          >
                                              <span class="popover-label">${xe(e.label)}</span>
                                              ${t?B`<span class="popover-check">&#10003;</span>`:a?B`<span class="popover-existing">${i}</span>`:""}
                                          </button>
                                      `})}
                                  ${this._customActionOpen?B`
                                            <div class="custom-action-row">
                                                <input
                                                    class="custom-action-input"
                                                    type="text"
                                                    placeholder=${ke("devdetail.custom_action_placeholder")}
                                                    .value=${this._customActionValue}
                                                    @input=${e=>this._customActionValue=e.target.value}
                                                    @keydown=${e=>{"Enter"===e.key&&this._customActionValue.trim()&&this._selectAction(this._mappingCommandName,this._customActionValue.trim())}}
                                                />
                                                <button
                                                    class="custom-action-set"
                                                    ?disabled=${!this._customActionValue.trim()}
                                                    @click=${()=>this._selectAction(this._mappingCommandName,this._customActionValue.trim())}
                                                >
                                                    ${ke("devdetail.set")}
                                                </button>
                                            </div>
                                        `:B`
                                            <button
                                                class="popover-item custom-action-open"
                                                @click=${e=>{e.stopPropagation(),this._customActionOpen=!0,this.updateComplete.then(()=>{this.shadowRoot?.querySelector(".custom-action-input")?.focus()})}}
                                            >
                                                <span class="popover-label"
                                                    >${ke("devdetail.custom_action")}</span
                                                >
                                            </button>
                                        `}
                              </div>
                          `:""}
                </div>
            </div>

            <div class="footer-actions">
                <div class="add-group">
                    <button
                        class="action-btn"
                        title=${ke("devdetail.sniff_title")}
                        @click=${this._goToSniffer}
                        ?disabled=${this._busy}
                    >${ke("devdetail.sniffed")}</button>
                    <button
                        class="action-btn"
                        title=${ke("devdetail.clip_title")}
                        @click=${this._goToClips}
                        ?disabled=${this._busy}
                    >${ke("devdetail.clipped")}</button>
                    <button
                        class="action-btn"
                        title=${ke("devdetail.mirror_title")}
                        @click=${this._goToMirror}
                        ?disabled=${this._busy}
                    >${ke("devdetail.mirrored")}</button>
                </div>
                <button
                    class="action-btn delete-btn"
                    @click=${()=>this._confirmDelete=!0}
                    ?disabled=${this._busy}
                >${ke("devlist.del_device_title")}</button>
            </div>

            <!-- Dialogs -->
            ${this._captureName?B`
                      <ir-capture-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          .commandName=${this._captureName}
                          @closed=${this._onCaptureClosed}
                          @command-saved=${this._onCommandSaved}
                      ></ir-capture-dialog>
                  `:""}
            ${this._confirmDelete?B`
                      <ir-confirm-dialog
                          title=${ke("devdetail.del_device_title",{name:this.device.name})}
                          message=${ke("devdetail.del_device_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._deleteDevice}
                          @closed=${()=>this._confirmDelete=!1}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._commandToDelete?B`
                      <ir-confirm-dialog
                          title=${ke("devdetail.del_cmd_title")}
                          message=${ke("devdetail.del_cmd_msg",{name:this._commandToDelete.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${()=>this._commandToDelete=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._editCommand?B`
                      <ir-signal-editor
                          .api=${this.api}
                          .deviceId=${this.device.id}
                          .commandId=${this._editCommand.id}
                          .initialPronto=${this._editCommand.code??""}
                          .initialAlias=${this._editCommand.name}
                          .initialSendCount=${this._editCommand.send_count??1}
                          .initialDitto=${this._editCommand.repeat_count??1}
                          .initialTxForceRaw=${this._editCommand.tx_force_raw??!1}
                          .initialDecodedProtocol=${this._editCommand.decoded_protocol??null}
                          .hasTrigger=${this._commandHasTrigger(this._editCommand)}
                          @command-edited=${this._onCommandEdited}
                          @closed=${()=>this._editCommand=null}
                      ></ir-signal-editor>
                  `:""}
            ${this._triggerPopover?B`
                      <ir-trigger-popover
                          .triggers=${this._triggersForCommand(this._triggerPopover.command)}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onTriggerPopoverCreateNew}
                          @edit-trigger=${this._onTriggerPopoverEdit}
                      ></ir-trigger-popover>
                  `:""}
            ${this._triggerCommand?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .protocol=${this._triggerCommand.protocol}
                          .code=${this._triggerCommand.code}
                          .byteHash=${this._triggerCommand.byte_hash??null}
                          .decodedFingerprint=${this._triggerCommand.decoded_fingerprint??null}
                          .sourceDeviceId=${this.device.id}
                          .sourceCommandId=${this._triggerCommand.id}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._triggerEdit?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEdit}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?B`
                      <ir-confirm-dialog
                          title=${ke("mirror.del_trigger_title")}
                          message=${ke("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._toast?B`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};ea.styles=[Li,Yi,n`
        :host {
            display: block;
        }

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }
        .header-left {
            flex: 1;
            min-width: 0;
        }
        h1 {
            font-size: 1.5rem;
            margin: 0;
        }
        .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .edit-icon {
            font-size: 0.75rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .edit-icon {
            opacity: 1;
        }
        .name-input {
            font-size: 1.5rem;
            font-family: inherit;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            width: 100%;
            padding: 0 0 2px;
        }
        .header .action-btn.collapse-btn {
            flex-shrink: 0;
            align-self: center;
        }

        /* --- Metadata grid --- */
        .device-meta {
            display: grid;
            grid-template-columns: 80px 1fr;
            gap: 8px 12px;
            align-items: start;
            margin: 16px 0 0;
        }
        .meta-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            padding-top: 6px;
        }
        .meta-value select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .meta-value ir-emitter-picker {
            --picker-label-display: none;
        }

        /* --- Buttons --- */
        .action-btn.collapse-btn {
            font-size: 1rem;
            padding: 2px 8px;
            color: var(--secondary-text-color);
            border-color: transparent;
        }
        .action-btn.collapse-btn:hover {
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
        }

        /* --- Commands section (Sniffer-style) --- */
        .commands-section {
            margin: 16px 0;
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
        }
        .commands-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--primary-text-color);
        }
        .commands-list {
            display: flex;
            flex-direction: column;
        }
        /* --- Drag handle (slotted into ir-command-row's status column) --- */
        .grip-handle {
            --mdc-icon-size: 18px;
            color: var(--secondary-text-color);
            opacity: 0.6;
            cursor: grab;
            transition: opacity 120ms ease;
        }
        .grip-handle:hover {
            opacity: 1;
        }
        .grip-handle:active {
            cursor: grabbing;
        }
        /* SortableJS applies this class to the element being dragged. */
        ir-command-row.sortable-ghost {
            opacity: 0.4;
        }
        /* Action-popover styles live in the shared ir-popover-styles module
           (spread into static styles below) so ir-trigger-popover reuses the
           exact same treatment. */
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        .footer-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 16px 0;
            flex-wrap: wrap;
            gap: 8px;
        }
        .add-group {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .add-label {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }

        /* --- Toast --- */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--primary-color);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            z-index: 100;
        }

        /* Custom action entry (free-form key) inside the Map action
           popover. Input + Set on one row, matching popover chrome. */
        .custom-action-row {
            display: flex;
            gap: 6px;
            padding: 6px 10px 8px;
            align-items: center;
        }
        .custom-action-input {
            flex: 1;
            min-width: 0;
            padding: 5px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.8rem;
            font-family: var(--code-font-family, monospace);
            box-sizing: border-box;
        }
        .custom-action-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .custom-action-set {
            border: 1px solid var(--divider-color);
            background: none;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            color: var(--primary-text-color);
        }
        .custom-action-set:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .custom-action-set:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
    `],e([pe({attribute:!1})],ea.prototype,"api",void 0),e([pe({attribute:!1})],ea.prototype,"hass",void 0),e([pe({attribute:!1})],ea.prototype,"device",void 0),e([ge()],ea.prototype,"_busy",void 0),e([ge()],ea.prototype,"_captureName",void 0),e([ge()],ea.prototype,"_toast",void 0),e([ge()],ea.prototype,"_confirmDelete",void 0),e([ge()],ea.prototype,"_commandToDelete",void 0),e([ge()],ea.prototype,"_editCommand",void 0),e([ge()],ea.prototype,"_actionOptions",void 0),e([ge()],ea.prototype,"_mappingCommandName",void 0),e([ge()],ea.prototype,"_popoverTop",void 0),e([ge()],ea.prototype,"_popoverLeft",void 0),e([ge()],ea.prototype,"_customActionOpen",void 0),e([ge()],ea.prototype,"_customActionValue",void 0),e([ge()],ea.prototype,"_editingName",void 0),e([ge()],ea.prototype,"_draftName",void 0),e([ge()],ea.prototype,"_triggers",void 0),e([ge()],ea.prototype,"_triggerCommand",void 0),e([ge()],ea.prototype,"_triggerEdit",void 0),e([ge()],ea.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],ea.prototype,"_triggerPopover",void 0),e([ge()],ea.prototype,"_receivers",void 0),e([ge()],ea.prototype,"_commandsListVersion",void 0),ea=e([ue("ir-device-detail")],ea);let ta=class extends se{constructor(){super(...arguments),this.sourceId="",this.sourceName="",this._name="",this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._name=`${this.sourceName} (Copy)`}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _duplicate(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.duplicateDevice(this.sourceId,e);this.dispatchEvent(new CustomEvent("device-duplicated",{detail:t,bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("common.name_required")}_onKeyDown(e){"Enter"===e.key&&(e.preventDefault(),this._duplicate())}render(){return B`
            <ha-dialog
                open
                heading=${ke("dup.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="hint">
                    ${ke("dup.hint_duplicating").split("{name}")[0]}<strong
                        >${this.sourceName}</strong
                    >${ke("dup.hint_duplicating").split("{name}")[1]??""}
                    ${ke("dup.hint_body")}
                </p>

                <div class="field">
                    <label>${ke("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        autofocus
                        required
                        @input=${e=>this._name=e.target.value}
                        @keydown=${this._onKeyDown}
                        @focus=${e=>e.target.select()}
                    />
                </div>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._duplicate}
                        ?disabled=${this._busy||!this._name.trim()}
                    >
                        ${this._busy?ke("dup.duplicating"):ke("dup.duplicate")}
                    </button>
                </div>
            </ha-dialog>
        `}};ta.styles=[Bi,n`
        .hint {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 8px 0 16px;
        }
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
        }
        .field input {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        .field input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        /* Slimmer actions row than the shared one; ships this way. */
        .dialog-actions {
            margin-top: 16px;
            padding-top: 0;
            border-top: none;
        }
        /* Opacity in the transition so the Create hover fades, not snaps. */
        .action-btn {
            transition: background 150ms ease, opacity 150ms ease;
        }
        /* Brighter cancel than the shared secondary; ships this way. */
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ta.prototype,"api",void 0),e([pe({attribute:!1})],ta.prototype,"sourceId",void 0),e([pe({attribute:!1})],ta.prototype,"sourceName",void 0),e([ge()],ta.prototype,"_name",void 0),e([ge()],ta.prototype,"_busy",void 0),e([ge()],ta.prototype,"_error",void 0),ta=e([ue("ir-duplicate-device-dialog")],ta);const ia={media_player:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",light:"M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",switch:"M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",screen:"M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},aa={media_player:"device_type.media_player",ac:"device_type.ac",fan:"device_type.fan",light:"device_type.light",switch:"device_type.switch",screen:"device_type.screen",other:"device_type.other_card"},ra="M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";let oa=class extends se{constructor(){super(...arguments),this.devices=[],this.loading=!1,this.expandedDeviceId=null,this._emitters=[],this._captureProviders=[],this._pluckBlasters=[],this._expandedDevice=null,this._triggers=[],this._glowTriggerIds=new Set,this._editTrigger=null,this._confirmDeleteTrigger=null,this._duplicateTarget=null,this._confirmDeleteDevice=null,this._devicesVersion=0,this._localDevices=null,this._devicesSortable=null,this._pendingDevicesSave=null,this._unsubTriggerFired=null}connectedCallback(){super.connectedCallback(),this._discoverHardware(),this._loadTriggers(),this._subscribeTriggerFired()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeTriggerFired(),this._devicesSortable?.destroy(),this._devicesSortable=null,null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave)}willUpdate(e){e.has("devices")&&(this._localDevices=null)}updated(e){(e.has("hass")||e.has("api"))&&this._discoverHardware(),e.has("api")&&this.api&&!this._unsubTriggerFired&&(this._loadTriggers(),this._subscribeTriggerFired()),e.has("expandedDeviceId")&&this._loadExpandedDevice(),this._syncDevicesSortable()}_syncDevicesSortable(){const e=this.renderRoot.querySelector(".device-grid");e&&!this._devicesSortable?this._attachDevicesSortable(e):!e&&this._devicesSortable&&(this._devicesSortable.destroy(),this._devicesSortable=null)}_attachDevicesSortable(e){this._devicesSortable=bi.create(e,{draggable:".device-card",filter:".card-action",preventOnFilter:!1,delay:150,delayOnTouchOnly:!0,animation:150,ghostClass:"sortable-ghost",onEnd:()=>{const t=Array.from(e.querySelectorAll(".device-card")).map(e=>e.dataset.id).filter(e=>!!e),i=this._localDevices??this.devices,a=new Map(i.map(e=>[e.id,e])),r=t.map(e=>a.get(e)).filter(e=>!!e);if(r.length===i.length){this._localDevices=r,this._devicesSortable?.destroy(),this._devicesSortable=null;for(const t of Array.from(e.querySelectorAll(".device-card, .expanded-detail")))t.remove();this._devicesVersion++,this._scheduleDevicesSave(r.map(e=>e.id))}}})}_scheduleDevicesSave(e){null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave),this._pendingDevicesSave=window.setTimeout(async()=>{if(this._pendingDevicesSave=null,this.api)try{await this.api.reorderDevices(e)}catch{this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}},500)}async _loadExpandedDevice(){if(this.expandedDeviceId&&this.api)try{this._expandedDevice=await this.api.getDevice(this.expandedDeviceId)}catch{this._expandedDevice=null}else this._expandedDevice=null}async _onExpandedDeviceChanged(){await this._loadExpandedDevice(),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_onExpandedDeviceDeleted(){this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}_onCommandsReordered(e){if(!this._expandedDevice)return;const t=e.detail?.commands;Array.isArray(t)&&(this._expandedDevice={...this._expandedDevice,commands:t})}_onCollapse(){this.dispatchEvent(new CustomEvent("device-selected",{detail:this.expandedDeviceId,bubbles:!0,composed:!0}))}async _discoverHardware(){const e=new Set;if(this.api)try{const t=await this.api.listReceivers();for(const i of t)e.add(i.entity_id)}catch{}const t=this.hass?.states??{},i=[];for(const[a,r]of Object.entries(t))!a.startsWith("infrared.")||e.has(a)||r.attributes.hair_observer||i.push({entity_id:a,name:r.attributes.friendly_name??a});if(this._emitters=i,this.api)try{this._captureProviders=await this.api.listCaptureProviders()}catch{}if(this.api)try{const{vendors:e}=await this.api.listPluckVendors(),t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entity_id:e.entity_id,name:e.name,vendorName:i.name});this._pluckBlasters=t}catch{this._pluckBlasters=[]}}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}_openInPlucker(e){this.dispatchEvent(new CustomEvent("navigate-plucker",{detail:{vendor_entity_id:e},bubbles:!0,composed:!0}))}_openDuplicateDialog(e,t){t.stopPropagation(),this._duplicateTarget=e}_closeDuplicateDialog(){this._duplicateTarget=null}_onDeviceDuplicated(){this._duplicateTarget=null,this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_requestDeleteDevice(e,t){t.stopPropagation(),this._confirmDeleteDevice=e}async _doDeleteDevice(){if(!this._confirmDeleteDevice||!this.api)return;const e=this._confirmDeleteDevice;this._confirmDeleteDevice=null;try{await this.api.deleteDevice(e.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch{}}_navigateIntegration(e){const t=`/config/integrations/integration/${e}`;window.history.pushState(null,"",t),window.dispatchEvent(new PopStateEvent("popstate"))}async _loadTriggers(){if(this.api)try{this._triggers=await this.api.listTriggers()}catch{}}async _subscribeTriggerFired(){if(this.api)try{this._unsubTriggerFired=await this.api.subscribeTriggerFired(e=>{this._glowTriggerIds=new Set([...this._glowTriggerIds,e.trigger_id]),setTimeout(()=>{const t=new Set(this._glowTriggerIds);t.delete(e.trigger_id),this._glowTriggerIds=t},2500)})}catch{}}async _unsubscribeTriggerFired(){this._unsubTriggerFired&&(await this._unsubTriggerFired(),this._unsubTriggerFired=null)}_openEditTrigger(e,t){t.stopPropagation(),this._editTrigger=e}_closeEditTrigger(){this._editTrigger=null}async _onTriggerUpdated(){this._editTrigger=null,await this._loadTriggers()}async _toggleTriggerEnabled(e,t){t.stopPropagation();try{await this.api.updateTrigger(e.id,{enabled:!e.enabled}),await this._loadTriggers()}catch{}}_requestDeleteTrigger(e,t){t.stopPropagation(),this._confirmDeleteTrigger=e}async _doDeleteTrigger(){if(!this._confirmDeleteTrigger)return;const e=this._confirmDeleteTrigger;this._confirmDeleteTrigger=null;try{await this.api.deleteTrigger(e.id),await this._loadTriggers()}catch{}}_emitterIntegrationDomain(e){const t=this.hass?.entities?.[e];return t?.platform?t.platform:e.split(".")[0]}_getEmitterDeviceIds(){const e=new Set;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id];i?.device_id&&e.add(i.device_id)}return e}_getEmitterEntityIdsByDevice(){const e=new Map;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id],a=i?.device_id;if(!a)continue;const r=e.get(a)??[];r.push(t.entity_id),e.set(a,r)}return e}_isPre2026_6(){const e=this.hass?.config?.version;if(!e)return!1;const t=e.match(/^(\d+)\.(\d+)/);if(!t)return!1;const i=parseInt(t[1],10),a=parseInt(t[2],10);return i<2026||2026===i&&a<6}_resolveNavType(e,t){if("native"===e.type&&t){const e=this.hass?.entities?.[t]?.platform;return e||"esphome"}return e.type}_classifyHardware(){const e=this._getEmitterEntityIdsByDevice(),t=new Set(e.keys()),i=new Map;for(const a of this._captureProviders){let r,o;if("native"===a.type?(o=a.receiver_entity_id??a.device_id,r=this.hass?.entities?.[o]?.device_id,r||(r=o)):r=a.device_id,!r)continue;const n=i.get(r)??{device_id:r,name:a.name,nav_type:this._resolveNavType(a,o),has_native:!1,has_bridge:!1,has_tx:t.has(r),tx_entity_ids:e.get(r)??[]};"native"===a.type?(n.has_native=!0,n.native_entity_id=o):(n.has_bridge=!0,n.name=a.name,n.nav_type=a.type),i.set(r,n)}const a=Array.from(i.values()),r=a.filter(e=>e.has_tx);return{receivers:a,proxies:r}}_renderRxBadges(e){const t=!e.has_native&&e.has_bridge&&this._isPre2026_6();return B`
            ${e.has_native?B`<span
                      class="badge rx-native"
                      title=${ke("devlist.rx_native_title")}
                  >RX-NATIVE</span>`:F}
            ${e.has_bridge?B`<span
                      class="badge rx-bridge"
                      title=${e.has_native?ke("devlist.rx_bridge_active"):ke("devlist.rx_bridge_title")}
                  >RX-BRIDGE</span>`:F}
            ${t?B`<span
                      class="badge rx-native-disabled"
                      title=${ke("devlist.rx_upgrade_title")}
                  >RX-NATIVE</span>`:F}
        `}render(){if(this.loading)return B`<div class="loading">${ke("devlist.loading")}</div>`;const e=this._localDevices??this.devices,t=e.length>0,i=this._emitters.length>0,{receivers:a,proxies:r}=this._classifyHardware(),o=a.length>0,n=r.length>0,s=this._triggers.length>0;return t||i||o||n?B`
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${"M17.655 0C17.391 0.034 17.201 0.276 17.235 0.54C17.269 0.804 17.511 0.994 17.775 0.96C17.775 0.96 18.154 0.941 18.81 1.155C19.466 1.369 20.353 1.804 21.255 2.73C22.162 3.66 22.611 4.551 22.83 5.205C23.049 5.859 23.04 6.24 23.04 6.24C23.038 6.412 23.128 6.574 23.278 6.662C23.428 6.748 23.612 6.748 23.762 6.662C23.912 6.574 24.002 6.412 24 6.24C24 6.24 23.991 5.679 23.73 4.905C23.469 4.131 22.957 3.109 21.945 2.07C20.927 1.027 19.894 0.495 19.11 0.24C18.326 -0.015 17.745 0 17.745 0C17.73 0 17.715 0 17.7 0C17.685 0 17.67 0 17.655 0 Z M 13.77 2.88C13.26 2.88 12.746 3.064 12.345 3.435C12.339 3.441 12.336 3.444 12.33 3.45L0.57 15.255C-0.195 16.02 -0.188 17.286 0.555 18.09C0.561 18.096 0.564 18.099 0.57 18.105L5.955 23.475C6.72 24.24 7.971 24.232 8.775 23.49C8.781 23.484 8.784 23.481 8.79 23.475L20.55 11.715C20.556 11.706 20.561 11.694 20.565 11.685C21.289 10.841 21.315 9.6 20.55 8.835L15.165 3.45C14.782 3.067 14.28 2.88 13.77 2.88 Z M 17.67 2.88C17.406 2.904 17.211 3.141 17.235 3.405C17.259 3.669 17.496 3.864 17.76 3.84C17.76 3.84 17.91 3.831 18.21 3.93C18.51 4.029 18.911 4.241 19.335 4.665C19.759 5.089 19.971 5.49 20.07 5.79C20.169 6.09 20.16 6.24 20.16 6.24C20.158 6.412 20.248 6.574 20.398 6.662C20.548 6.748 20.732 6.748 20.882 6.662C21.032 6.574 21.122 6.412 21.12 6.24C21.12 6.24 21.111 5.91 20.97 5.49C20.829 5.07 20.561 4.511 20.025 3.975C19.489 3.439 18.93 3.171 18.51 3.03C18.09 2.889 17.76 2.88 17.76 2.88C17.745 2.88 17.73 2.88 17.715 2.88C17.7 2.88 17.685 2.88 17.67 2.88 Z M 13.77 3.84C14.04 3.84 14.297 3.932 14.49 4.125L19.875 9.51C20.263 9.898 20.274 10.569 19.845 11.07L8.115 22.785C7.671 23.194 7.018 23.188 6.63 22.8L1.26 17.43C1.254 17.424 1.251 17.421 1.245 17.415C0.849 16.971 0.862 16.328 1.245 15.945L13.005 4.14C13.226 3.936 13.5 3.84 13.77 3.84 Z M 13.44 6.72C11.325 6.72 9.6 8.445 9.6 10.56C9.6 12.675 11.325 14.4 13.44 14.4C15.555 14.4 17.28 12.675 17.28 10.56C17.28 8.445 15.555 6.72 13.44 6.72 Z M 13.44 7.68C15.036 7.68 16.32 8.964 16.32 10.56C16.32 12.156 15.036 13.44 13.44 13.44C11.844 13.44 10.56 12.156 10.56 10.56C10.56 8.964 11.844 7.68 13.44 7.68 Z M 13.44 9.6C12.909 9.6 12.48 10.029 12.48 10.56C12.48 11.091 12.909 11.52 13.44 11.52C13.971 11.52 14.4 11.091 14.4 10.56C14.4 10.029 13.971 9.6 13.44 9.6 Z M 7.2 12.96C6.669 12.96 6.24 13.389 6.24 13.92C6.24 14.451 6.669 14.88 7.2 14.88C7.731 14.88 8.16 14.451 8.16 13.92C8.16 13.389 7.731 12.96 7.2 12.96 Z M 4.8 15.36C4.269 15.36 3.84 15.789 3.84 16.32C3.84 16.851 4.269 17.28 4.8 17.28C5.331 17.28 5.76 16.851 5.76 16.32C5.76 15.789 5.331 15.36 4.8 15.36 Z M 10.08 15.84C9.549 15.84 9.12 16.269 9.12 16.8C9.12 17.331 9.549 17.76 10.08 17.76C10.611 17.76 11.04 17.331 11.04 16.8C11.04 16.269 10.611 15.84 10.08 15.84 Z M 7.68 18.24C7.149 18.24 6.72 18.669 6.72 19.2C6.72 19.731 7.149 20.16 7.68 20.16C8.211 20.16 8.64 19.731 8.64 19.2C8.64 18.669 8.211 18.24 7.68 18.24Z"}></ha-svg-icon>
                    ${ke("devlist.title")}
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
                <button class="add-btn" @click=${this._add}>
                    <ha-svg-icon
                        .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                    ></ha-svg-icon>
                    ${ke("devlist.add_device")}
                </button>
            </div>
            ${t?B`
                      <div class="grid device-grid">
                          ${He(this._devicesVersion,Me(e,e=>e.id,e=>B`
                                  <div
                                      class="card device-card ${e.id===this.expandedDeviceId?"expanded":""}"
                                      data-id=${e.id}
                                      tabindex="0"
                                      @click=${()=>this._select(e.id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._select(e.id))}}
                                  >
                                      <button
                                          class="card-action duplicate-action"
                                          title=${ke("dup.heading")}
                                          @click=${t=>this._openDuplicateDialog(e,t)}
                                      >
                                          <ha-svg-icon .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}></ha-svg-icon>
                                      </button>
                                      <button
                                          class="card-action delete-action"
                                          title=${ke("devlist.delete_device")}
                                          @click=${t=>this._requestDeleteDevice(e,t)}
                                      >
                                          <ha-svg-icon .path=${ra}></ha-svg-icon>
                                      </button>
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${ia[e.device_type]??ia.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[e.manufacturer,ke(aa[e.device_type])].filter(Boolean).join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              ${ke("devlist.cmd_badge",{count:e.command_count})}
                                          </span>
                                          ${e.emitter_entity_ids.length>0?B`<span class="badge tx-badge">${ke("devlist.tx_badge",{count:e.emitter_entity_ids.length})}</span>`:B`<span class="badge no-tx-badge">${ke("devlist.no_tx")}</span>`}
                                      </div>
                                  </div>
                                  ${e.id===this.expandedDeviceId&&this._expandedDevice?B`
                                            <div class="expanded-detail">
                                                <ir-device-detail
                                                    .api=${this.api}
                                                    .device=${this._expandedDevice}
                                                    .hass=${this.hass}
                                                    @device-changed=${this._onExpandedDeviceChanged}
                                                    @device-deleted=${this._onExpandedDeviceDeleted}
                                                    @commands-reordered=${this._onCommandsReordered}
                                                    @trigger-changed=${this._loadTriggers}
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `:F}
                              `))}
                      </div>
                  `:B`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Triggers -->
            ${s?B`
                      <div class="section-header">
                          <h2>${ke("popover.triggers")}</h2>
                          <span class="section-count">${this._triggers.length}</span>
                      </div>
                      <div class="grid">
                          ${this._triggers.map(e=>B`
                                  <div
                                      class="card trigger-card ${this._glowTriggerIds.has(e.id)?"trigger-glow":""} ${e.enabled?"":"trigger-disabled"}"
                                      tabindex="0"
                                      @click=${t=>this._openEditTrigger(e,t)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._openEditTrigger(e,t))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon class="trigger-icon" .path=${"M7,2V13H10V22L17,10H13L17,2H7Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${ke("trigger.event")}</div>
                                      <div class="card-footer">
                                          ${e.min_hits>1?B`<span class="badge trigger-hits-badge">
                                                    ${ke("devlist.hits_badge",{count:e.min_hits})}
                                                </span>`:F}
                                          <span
                                              class="badge trigger-toggle ${e.enabled?"trigger-enabled":"trigger-off"}"
                                              @click=${t=>this._toggleTriggerEnabled(e,t)}
                                          >${e.enabled?ke("devlist.on"):ke("devlist.off")}</span>
                                          <ha-svg-icon
                                              class="trigger-trash"
                                              .path=${ra}
                                              title=${ke("devlist.delete_trigger")}
                                              @click=${t=>this._requestDeleteTrigger(e,t)}
                                          ></ha-svg-icon>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:F}

            <!-- Blasters (Pluckable) -- vendor IR blasters HAIR can pull from -->
            ${this._pluckBlasters.length>0?B`
                      <div class="section-header">
                          <h2>${ke("devlist.blasters")}</h2>
                          <span class="section-count"
                              >${this._pluckBlasters.length}</span
                          >
                      </div>
                      <div class="grid">
                          ${this._pluckBlasters.map(e=>B`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      title=${ke("devlist.open_plucker_title")}
                                      @click=${()=>this._openInPlucker(e.entity_id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._openInPlucker(e.entity_id))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z"}></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.vendorName}: ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">${e.entity_id}</div>
                                      <div class="card-footer">
                                          <span class="badge pluck-badge"
                                              >${ke("devlist.open_plucker")}</span
                                          >
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:F}

            <!-- Emitters -->
            ${i?B`
                      <div class="section-header">
                          <h2>${ke("devlist.emitters")}</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(e=>B`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(this._emitterIntegrationDomain(e.entity_id))}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(this._emitterIntegrationDomain(e.entity_id)))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M9,10V16H15V10H19L12,3L5,10H9M12,5.8L14.2,8H13V14H11V8H9.8L12,5.8M19,18H5V20H19V18Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.entity_id}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${ke("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:F}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${o?B`
                      <div class="section-header">
                          <h2>${ke("devlist.receivers")}</h2>
                          <span class="section-count">${a.length}</span>
                      </div>
                      <div class="grid">
                          ${a.map(e=>B`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.nav_type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.nav_type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.native_entity_id??e.nav_type}</div>
                                      <div class="card-footer">
                                          ${this._renderRxBadges(e)}
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:F}

            <!-- Proxies (TX + RX hardware) -->
            ${n?B`
                      <div class="section-header">
                          <h2>${ke("devlist.proxies")}</h2>
                          <span class="section-count">${r.length}</span>
                      </div>
                      <div class="grid">
                          ${r.map(e=>B`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.nav_type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.nav_type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      ${e.tx_entity_ids[0]?B`<div class="card-meta">${e.tx_entity_ids[0]}</div>`:F}
                                      <div class="card-meta">${e.native_entity_id??e.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${ke("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                          ${this._renderRxBadges(e)}
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:F}

            ${this._editTrigger?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `:F}

            ${this._confirmDeleteTrigger?B`
                      <ir-confirm-dialog
                          title=${ke("mirror.del_trigger_title")}
                          message=${ke("devlist.del_trigger_msg",{name:this._confirmDeleteTrigger.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTrigger=null}
                      ></ir-confirm-dialog>
                  `:F}

            ${this._duplicateTarget&&this.api?B`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `:F}

            ${this._confirmDeleteDevice?B`
                      <ir-confirm-dialog
                          title=${ke("devlist.del_device_title")}
                          message=${ke("devlist.del_device_msg",{name:this._confirmDeleteDevice.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${()=>this._confirmDeleteDevice=null}
                      ></ir-confirm-dialog>
                  `:F}
        `:B`
                <ha-card class="empty">
                    <h2>${ke("devlist.empty_title")}</h2>
                    <p>${ke("devlist.empty_sub")}</p>
                    <mwc-button raised @click=${this._add}>${ke("devlist.add_device_plus")}</mwc-button>
                </ha-card>
            `}};oa.styles=n`
        :host {
            display: block;
        }
        .loading,
        .empty {
            padding: 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty h2 {
            margin-top: 8px;
            color: var(--primary-text-color);
        }

        .empty-devices {
            text-align: center;
            padding: 24px 16px;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin-bottom: 16px;
        }

        /* --- Devices toolbar (matches sniffer) --- */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .toolbar-title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--primary-color);
        }
        .add-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: none;
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            padding: 4px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .add-btn ha-svg-icon {
            --mdc-icon-size: 18px;
        }
        .add-btn:hover {
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.08);
        }
        .toolbar-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }

        /* --- Section headers (neutral) --- */
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 24px 0 10px;
            padding-bottom: 6px;
            border-bottom: 2px solid var(--divider-color);
        }
        .section-header:first-child {
            margin-top: 0;
        }
        .section-header h2 {
            margin: 0;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            color: var(--secondary-text-color);
        }
        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
        }

        /* --- Card grid (compact) --- */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
        }

        /* --- Shared card styles (neutral, sniffer palette) --- */
        .card {
            padding: 12px;
            cursor: pointer;
            border-radius: 8px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .card:hover,
        .card:focus-visible {
            background: var(--secondary-background-color);
            outline: none;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-header ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            /* Long card names (eg the Athom proxy transmitter title) can
               otherwise squeeze the flex item below its intrinsic size. */
            flex-shrink: 0;
        }
        .card-name {
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-meta {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 8px;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 0.72rem;
            font-weight: 500;
        }

        /* Command count badge (green) */
        .cmd-badge {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }

        /* TX badge (amber text, dark bg) */
        .tx-badge {
            background: var(--secondary-background-color);
            color: #ff9800;
        }

        /* RX badge (blue text, dark bg) */
        .rx-badge {
            background: var(--secondary-background-color);
            color: var(--primary-color, #2196f3);
        }

        /* No TX warning (muted) */
        .no-tx-badge {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            font-style: italic;
        }

        /* Hardware section badges -- consistent <direction>-<source> pattern. */
        /* TX-NATIVE and RX-NATIVE share the green palette of .cmd-badge. */
        .tx-native,
        .rx-native {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        /* RX-BRIDGE uses HAIR's existing orange. */
        .rx-bridge {
            background: rgba(255, 152, 0, 0.15);
            color: #ff9800;
        }
        /* Pre-2026.6 upgrade hint: grayed RX-NATIVE alongside RX-BRIDGE. */
        .rx-native-disabled {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            opacity: 0.6;
            cursor: help;
        }

        /* --- Expanded detail row --- */
        .expanded-detail {
            grid-column: 1 / -1;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            padding: 16px;
            animation: expand-in 200ms ease;
        }
        @keyframes expand-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Device card expanded highlight --- */
        .device-card {
            position: relative;
        }
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }
        /* SortableJS marks the card being dragged. */
        .device-card.sortable-ghost {
            opacity: 0.4;
        }
        .device-card.sortable-chosen {
            cursor: grabbing;
        }

        /* --- Card corner actions (duplicate top-right, delete bottom-right) --- */
        .card-action {
            position: absolute;
            background: transparent;
            border: none;
            padding: 4px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 120ms ease, color 120ms ease, opacity 120ms ease;
        }
        .card-action ha-svg-icon {
            /* Default card-action glyph size. The duplicate-action overrides
               this with a smaller value because the copy MDI glyph fills more
               of its viewbox than the trash glyph. */
            --mdc-icon-size: 16px;
        }
        .duplicate-action {
            top: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0.55;
        }
        .duplicate-action ha-svg-icon {
            /* Copy MDI glyph fills more of its viewbox than the trash glyph,
               so render it smaller to land at the same visual size as the
               trash icon in the opposite corner. */
            --mdc-icon-size: 13px;
        }
        .duplicate-action:hover {
            color: var(--primary-text-color);
            opacity: 1;
        }
        .delete-action {
            bottom: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0.55;
        }
        .delete-action:hover {
            background: rgba(244, 67, 54, 0.12);
            color: #f44336;
            opacity: 1;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }
        /* "Open in Plucker" badge -- standard badge form, no stroke. */
        .pluck-badge {
            background: var(--secondary-background-color);
            color: #78909c;
            text-transform: uppercase;
        }

        /* --- Trigger section --- */
        .trigger-card {
            transition: transform 120ms ease, box-shadow 300ms ease,
                        border-color 300ms ease, background 400ms ease;
        }
        .trigger-card .trigger-icon {
            transition: color 200ms ease, transform 200ms ease;
        }
        .trigger-card.trigger-disabled {
            opacity: 0.5;
        }

        /* --- Trigger fire animation (card + bolt) --- */
        .trigger-card.trigger-glow {
            border-color: #d4a017;
            background: rgba(212, 160, 23, 0.08);
            animation: trigger-card-flash 2.4s ease-out;
        }
        .trigger-card.trigger-glow .trigger-icon {
            color: #f5a623;
            animation: trigger-bolt-pulse 2.4s ease-out;
        }
        @keyframes trigger-card-flash {
            0% {
                background: rgba(212, 160, 23, 0.18);
                border-color: #f5a623;
                box-shadow: 0 0 16px 4px rgba(245, 166, 35, 0.4);
            }
            30% {
                background: rgba(212, 160, 23, 0.1);
                border-color: #d4a017;
                box-shadow: 0 0 8px 2px rgba(245, 166, 35, 0.2);
            }
            60% {
                background: rgba(212, 160, 23, 0.06);
                box-shadow: 0 0 4px 1px rgba(245, 166, 35, 0.1);
            }
            100% {
                background: transparent;
                border-color: var(--divider-color);
                box-shadow: none;
            }
        }
        @keyframes trigger-bolt-pulse {
            0% { color: #ffb300; transform: scale(1.4); }
            15% { color: #f5a623; transform: scale(1.0); }
            30% { color: #ffb300; transform: scale(1.35); }
            50% { color: #d4a017; transform: scale(1.0); }
            100% { color: var(--secondary-text-color); transform: scale(1.0); }
        }
        .trigger-hits-badge {
            background: rgba(184, 153, 48, 0.15);
            color: #b89930;
            text-transform: uppercase;
        }
        .trigger-toggle {
            cursor: pointer;
            transition: background 150ms ease;
        }
        .trigger-toggle.trigger-enabled {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        .trigger-toggle.trigger-enabled:hover {
            background: rgba(46, 125, 50, 0.25);
        }
        .trigger-toggle.trigger-off {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
        }
        .trigger-toggle.trigger-off:hover {
            background: rgba(0, 0, 0, 0.1);
        }
        /* Matches the device-card .delete-action palette so the trigger
           trash and the device-card trash read as the same control. */
        .trigger-trash {
            --mdc-icon-size: 16px;
            color: var(--disabled-text-color, #999);
            cursor: pointer;
            margin-left: auto;
            opacity: 0.55;
            border-radius: 4px;
            padding: 2px;
            transition: background 150ms ease, color 150ms ease, opacity 150ms ease;
        }
        .trigger-trash:hover {
            background: rgba(244, 67, 54, 0.12);
            color: #f44336;
            opacity: 1;
        }
    `,e([pe({attribute:!1})],oa.prototype,"devices",void 0),e([pe({attribute:!1})],oa.prototype,"hass",void 0),e([pe({attribute:!1})],oa.prototype,"api",void 0),e([pe({type:Boolean})],oa.prototype,"loading",void 0),e([pe({attribute:!1})],oa.prototype,"expandedDeviceId",void 0),e([ge()],oa.prototype,"_emitters",void 0),e([ge()],oa.prototype,"_captureProviders",void 0),e([ge()],oa.prototype,"_pluckBlasters",void 0),e([ge()],oa.prototype,"_expandedDevice",void 0),e([ge()],oa.prototype,"_triggers",void 0),e([ge()],oa.prototype,"_glowTriggerIds",void 0),e([ge()],oa.prototype,"_editTrigger",void 0),e([ge()],oa.prototype,"_confirmDeleteTrigger",void 0),e([ge()],oa.prototype,"_duplicateTarget",void 0),e([ge()],oa.prototype,"_confirmDeleteDevice",void 0),e([ge()],oa.prototype,"_devicesVersion",void 0),e([ge()],oa.prototype,"_localDevices",void 0),oa=e([ue("ir-device-list")],oa);const na=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let sa=class extends se{constructor(){super(...arguments),this._name="",this._deviceType="media_player",this._emitterIds=[],this._captureProviders=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadCaptureProviders()}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{const e=this._captureProviders[0]??null,t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_ids:this._emitterIds,capture_device_id:e?.device_id??null,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("adddev.emitter_required");else this._error=ke("common.name_required")}render(){return B`
            <ha-dialog
                open
                heading=${ke("adddev.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${ke("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${ke("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>this._name=e.target.value}
                    />
                </div>

                <div class="field">
                    <label>${ke("common.device_type")}</label>
                    <select
                        .value=${this._deviceType}
                        @change=${e=>this._deviceType=e.target.value}
                    >
                        ${na.map(e=>B`
                                <option
                                    value=${e.value}
                                    ?selected=${this._deviceType===e.value}
                                >
                                    ${ke(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${e=>this._emitterIds=e.detail.value}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?ke("common.creating"):ke("adddev.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};sa.styles=[Bi,n`
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],sa.prototype,"api",void 0),e([pe({attribute:!1})],sa.prototype,"hass",void 0),e([ge()],sa.prototype,"_name",void 0),e([ge()],sa.prototype,"_deviceType",void 0),e([ge()],sa.prototype,"_emitterIds",void 0),e([ge()],sa.prototype,"_captureProviders",void 0),e([ge()],sa.prototype,"_busy",void 0),e([ge()],sa.prototype,"_error",void 0),sa=e([ue("ir-add-device-dialog")],sa);let la=class extends se{constructor(){super(...arguments),this.deviceId="",this.disabled=!1,this._editing=!1,this._draft=""}updated(e){if(e.has("_editing")&&this._editing){const e=this.shadowRoot?.querySelector(".alias-input");e?.focus(),e?.select()}}_startEdit(e){this.disabled||(e?.stopPropagation(),this._draft=this.signal.alias??"",this._editing=!0)}_onKeydown(e){"Enter"===e.key?this._commit():"Escape"===e.key&&(this._editing=!1)}async _commit(){if(!this._editing)return;const e=this._draft.trim();this._editing=!1,await this._save(e)}async _clear(){this._editing=!1,await this._save("")}async _save(e){try{await this.api.setSignalAlias(this.deviceId,this.signal.id,e),this.dispatchEvent(new CustomEvent("alias-changed",{detail:{id:this.signal.id,alias:e},bubbles:!0,composed:!0}))}catch(e){this.dispatchEvent(new CustomEvent("alias-error",{detail:e.message,bubbles:!0,composed:!0}))}}render(){const e=this.signal;return this._editing?B`
                <span class="alias-edit" @click=${e=>e.stopPropagation()}>
                    <input
                        class="alias-input"
                        type="text"
                        .value=${this._draft}
                        placeholder=${ke("alias.placeholder")}
                        @input=${e=>{this._draft=e.target.value}}
                        @keydown=${this._onKeydown}
                        @blur=${()=>{this._commit()}}
                    />
                    <button
                        class="alias-clear"
                        title=${ke("alias.clear")}
                        @mousedown=${e=>e.preventDefault()}
                        @click=${()=>{this._clear()}}
                    >✕</button>
                </span>
            `:e.alias?B`
                <span
                    class="alias-display ${this.disabled?"locked":""}"
                    title=${this.disabled?"":ke("alias.edit")}
                    @click=${e=>this._startEdit(e)}
                >
                    <span class="alias-label">${ke("alias.tag")}</span>
                    <span class="alias-name">${e.alias}</span>
                </span>
            `:B`
            <span
                class="diamonds-wrap ${this.disabled?"locked":""}"
                title=${this.disabled?"":ke("alias.name")}
                @click=${e=>this._startEdit(e)}
            >
                ${e.sl_pattern?B`<span class="diamonds"
                          >${[...e.sl_pattern].map(e=>"L"===e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}</span
                      >`:B`<span class="signal-short-label">IR Signal</span>`}
                <ha-svg-icon class="alias-pencil" .path=${"M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z"}></ha-svg-icon>
            </span>
        `}};la.styles=n`
        :host {
            display: inline-flex;
            align-items: center;
            min-width: 0;
        }
        .diamonds-wrap {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .diamonds-wrap.locked,
        .alias-display.locked {
            cursor: default;
        }
        .diamonds-wrap.locked .alias-pencil {
            display: none;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .alias-pencil {
            --mdc-icon-size: 13px;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .diamonds-wrap:hover .alias-pencil {
            opacity: 0.7;
        }
        .alias-display {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
            cursor: pointer;
        }
        .alias-label {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .alias-edit {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .alias-input {
            font-size: 0.85rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 150px;
        }
        .alias-clear {
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-size: 0.8rem;
            line-height: 1;
            padding: 3px 6px;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .alias-clear:hover {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.4);
        }
    `,e([pe({attribute:!1})],la.prototype,"api",void 0),e([pe()],la.prototype,"deviceId",void 0),e([pe({attribute:!1})],la.prototype,"signal",void 0),e([pe({type:Boolean})],la.prototype,"disabled",void 0),e([ge()],la.prototype,"_editing",void 0),e([ge()],la.prototype,"_draft",void 0),la=e([ue("ir-signal-alias")],la);const da=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let ca=class extends se{constructor(){super(...arguments),this.suggestedDeviceName="",this.initialMode="existing",this._mode="existing",this._devices=[],this._selectedDeviceId="",this._commandName="",this._newName="",this._newType="media_player",this._newEmitterIds=[],this._templates=[],this._customCommand=!1,this._sendCount=1,this._dittoCount=1,this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._mode=this.initialMode,this.suggestedDeviceName&&!this._newName&&(this._newName=this.suggestedDeviceName),this._sendCount=this.signal?.send_count??1,this._dittoCount=this.signal?.repeat_count??1,this._loadDevices(),"new"===this._mode&&this._loadTemplates(this._newType)}async _loadDevices(){try{if(this._devices=await this.api.listDevices(),this.suggestedDeviceName&&!this._selectedDeviceId){const e=this.suggestedDeviceName.toLowerCase(),t=this._devices.find(t=>t.name.toLowerCase()===e);if(t)return this._selectedDeviceId=t.id,void this._loadTemplates(t.device_type)}if("existing"===this._mode&&this._devices.length>0){const e=this._devices[0];this._loadTemplates(e.device_type)}else"existing"===this._mode&&this._loadTemplates("other")}catch{"existing"===this._mode&&this._loadTemplates("other")}}async _loadTemplates(e){try{this._templates=await this.api.listTemplates(e)}catch{this._templates=[]}this._customCommand||(this._commandName="")}_activeDeviceType(){if("new"===this._mode)return this._newType;const e=this._devices.find(e=>e.id===this._selectedDeviceId);return e?.device_type??"other"}_onDeviceSelected(e){this._selectedDeviceId=e.target.value;const t=this._devices.find(e=>e.id===this._selectedDeviceId);t&&this._loadTemplates(t.device_type)}_onNewTypeChanged(e){this._newType=e.target.value,this._loadTemplates(this._newType)}_switchMode(e){e!==this._mode&&(this._mode=e,this._customCommand=!1,this._commandName="",this._loadTemplates(this._activeDeviceType()))}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._dittoCount=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}async _assign(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{let t;if("existing"===this._mode){if(!this._selectedDeviceId)return this._error=ke("assign.target_required"),void(this._busy=!1);t=await this.api.assignSignal({device_id:this.unknownDeviceId,signal_id:this.signal.id,hair_device_id:this._selectedDeviceId,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}else{if(!this._newName.trim())return this._error=ke("promote.device_name_required"),void(this._busy=!1);if(0===this._newEmitterIds.length)return this._error=ke("promote.emitter_required"),void(this._busy=!1);t=await this.api.assignToNewDevice({device_id:this.unknownDeviceId,signal_id:this.signal.id,device_name:this._newName.trim(),device_type:this._newType,emitter_entity_ids:this._newEmitterIds,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}t.assigned?this.dispatchEvent(new CustomEvent("signal-assigned",{detail:t,bubbles:!0,composed:!0})):this._error=ke("assign.failed_duplicate")}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("assign.command_required")}_fmtTime(e){try{return new Date(e).toLocaleString(we(),{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}render(){const e=this.signal.frequency?`${Math.round(this.signal.frequency/1e3)}kHz`:"";return B`
            <ha-dialog
                open
                heading=${ke("assign.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="signal-header">
                    ${this.suggestedDeviceName?B`<div class="device-name">${this.suggestedDeviceName}</div>`:""}
                    <div class="signal-detail">
                        <ir-signal-alias
                            .api=${this.api}
                            .deviceId=${this.unknownDeviceId}
                            .signal=${this.signal}
                            disabled
                        ></ir-signal-alias>
                    </div>
                    <div class="signal-stats">
                        <span>${ke("assign.hits",{count:this.signal.hit_count})}</span>
                        ${e?B`<span>${e}</span>`:""}
                        <span>${this._fmtTime(this.signal.last_seen)}</span>
                    </div>
                </div>

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${"existing"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("existing")}}
                    >
                        ${ke("assign.mode_existing")}
                    </button>
                    <button
                        class="mode-tab ${"new"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("new")}}
                    >
                        ${ke("assign.mode_new")}
                    </button>
                </div>

                ${"existing"===this._mode?this._renderExistingMode():this._renderNewMode()}

                <!-- Command name (shared by both modes) -->
                ${this._renderCommandPicker()}

                <!-- Whole-frame send count (shared by both modes) -->
                <div class="field">
                    <label>${ke("assign.send_times")}</label>
                    <input
                        class="send-count"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._sendCount)}
                        @input=${this._onSendCountInput}
                    />
                    <div class="hint">
                        ${ke("assign.send_times_hint")}
                    </div>
                </div>

                ${this.signal.decoded_fingerprint?B`<!-- NEC ditto count (decoded signals only) -->
                          <div class="field">
                              <label>${ke("assign.ditto_count")}</label>
                              <input
                                  class="send-count"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._dittoCount)}
                                  title=${ke("assign.ditto_title")}
                                  @input=${this._onDittoInput}
                              />
                              <div class="hint">
                                  ${ke("assign.ditto_hint")}
                              </div>
                          </div>`:""}

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide assign-btn"
                        @click=${this._assign}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?ke("assign.assigning"):"new"===this._mode?ke("assign.create_assign"):ke("assign.assign")}
                    </button>
                </div>
            </ha-dialog>
        `}_renderExistingMode(){return B`
            <div class="field">
                <label>${ke("assign.target_device")}</label>
                ${0===this._devices.length?B`<ha-alert alert-type="info">
                          ${ke("assign.no_devices")}
                      </ha-alert>`:B`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>${ke("assign.select_device")}</option>
                              ${this._devices.map(e=>B`
                                      <option
                                          value=${e.id}
                                          ?selected=${this._selectedDeviceId===e.id}
                                      >
                                          ${e.name} (${e.device_type})
                                      </option>
                                  `)}
                          </select>
                      `}
            </div>
        `}_renderNewMode(){return B`
            <div class="field">
                <label>${ke("promote.device_name")}</label>
                <input
                    type="text"
                    .value=${this._newName}
                    placeholder=${ke("common.device_name_placeholder")}
                    required
                    autofocus
                    @input=${e=>this._newName=e.target.value}
                />
            </div>

            <div class="field">
                <label>${ke("common.device_type")}</label>
                <select
                    .value=${this._newType}
                    @change=${this._onNewTypeChanged}
                >
                    ${da.map(e=>B`
                            <option
                                value=${e.value}
                                ?selected=${this._newType===e.value}
                            >
                                ${ke(`device_type.${e.value}`)}
                            </option>
                        `)}
                </select>
            </div>

            <ir-emitter-picker
                .hass=${this.hass}
                .api=${this.api}
                .value=${this._newEmitterIds}
                ?disabled=${this._busy}
                @emitters-changed=${e=>this._newEmitterIds=e.detail.value}
            ></ir-emitter-picker>
        `}_onCommandSelect(e){const t=e.target.value;"__custom__"===t?(this._customCommand=!0,this._commandName="",this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".custom-cmd-input");e?.focus()})):(this._customCommand=!1,this._commandName=t)}_renderCommandPicker(){return this._customCommand?B`
                <div class="field">
                    <label>${ke("assign.command_name")}</label>
                    <div class="custom-cmd-row">
                        <input
                            class="custom-cmd-input"
                            type="text"
                            placeholder=${ke("assign.command_placeholder")}
                            .value=${this._commandName}
                            @input=${e=>this._commandName=e.target.value}
                        />
                        <button
                            class="back-link"
                            @click=${()=>{this._customCommand=!1,this._commandName=""}}
                        >${ke("common.cancel")}</button>
                    </div>
                </div>
            `:B`
            <div class="field">
                <label>${ke("assign.command_name")}</label>
                <select
                    .value=${this._commandName}
                    @change=${this._onCommandSelect}
                >
                    <option value="" disabled ?selected=${!this._commandName}>
                        ${ke("assign.select_command")}
                    </option>
                    ${this._templates.map(e=>B`
                            <option
                                value=${xe(e.name)}
                                ?selected=${this._commandName===xe(e.name)}
                            >
                                ${xe(e.name)}
                            </option>
                        `)}
                    <option value="__custom__">${ke("assign.custom")}</option>
                </select>
            </div>
        `}};ca.styles=[Bi,n`
        input.send-count {
            width: 80px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input.send-count:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        input.send-count:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .hint {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }

        .signal-header {
            padding: 10px 12px;
            background: var(--secondary-background-color);
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .device-name {
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 6px;
        }
        .signal-detail {
            margin-bottom: 4px;
        }
        .diamonds {
            font-size: 0.7rem;
            letter-spacing: 0px;
            line-height: 1;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .proto-label {
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--secondary-text-color);
        }
        .signal-stats {
            display: flex;
            gap: 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }

        .mode-tabs {
            display: flex;
            border-bottom: 1px solid var(--divider-color);
            margin: 12px 0;
        }
        .mode-tab {
            flex: 1;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-family: inherit;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .mode-tab:hover {
            color: var(--primary-text-color);
        }
        .mode-tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }

        .assign-btn {
            background: var(--primary-color);
            color: var(--text-primary-color, #fff);
        }
        .assign-btn:hover:not(:disabled) {
            opacity: 0.9;
        }

        /* --- Custom command input --- */
        .custom-cmd-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .custom-cmd-input {
            flex: 1;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.9rem;
        }
        .custom-cmd-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .back-link {
            background: none;
            border: none;
            color: var(--primary-color);
            font-size: 0.8rem;
            font-family: inherit;
            cursor: pointer;
            padding: 4px 8px;
            white-space: nowrap;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    `],e([pe({attribute:!1})],ca.prototype,"api",void 0),e([pe({attribute:!1})],ca.prototype,"hass",void 0),e([pe()],ca.prototype,"unknownDeviceId",void 0),e([pe({attribute:!1})],ca.prototype,"signal",void 0),e([pe()],ca.prototype,"suggestedDeviceName",void 0),e([pe()],ca.prototype,"initialMode",void 0),e([ge()],ca.prototype,"_mode",void 0),e([ge()],ca.prototype,"_devices",void 0),e([ge()],ca.prototype,"_selectedDeviceId",void 0),e([ge()],ca.prototype,"_commandName",void 0),e([ge()],ca.prototype,"_newName",void 0),e([ge()],ca.prototype,"_newType",void 0),e([ge()],ca.prototype,"_newEmitterIds",void 0),e([ge()],ca.prototype,"_templates",void 0),e([ge()],ca.prototype,"_customCommand",void 0),e([ge()],ca.prototype,"_sendCount",void 0),e([ge()],ca.prototype,"_dittoCount",void 0),e([ge()],ca.prototype,"_busy",void 0),e([ge()],ca.prototype,"_error",void 0),ca=e([ue("ir-assign-signal-dialog")],ca);const pa=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let ga=class extends se{constructor(){super(...arguments),this.suggestedName="",this._name="",this._type="other",this._emitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.suggestedName&&!this._name&&(this._name=this.suggestedName)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._name.trim();if(e)if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{await this.api.createDevice({name:e,device_type:this._type,emitter_entity_ids:this._emitterIds}),this.dispatchEvent(new CustomEvent("device-created",{bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("promote.emitter_required");else this._error=ke("promote.device_name_required")}render(){return B`
            <ha-dialog
                open
                heading=${ke("promote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="description">${ke("promote.description")}</p>

                <div class="field">
                    <label>${ke("promote.device_name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${ke("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>this._name=e.target.value}
                        @keydown=${e=>{"Enter"===e.key&&this._create()}}
                    />
                </div>

                <div class="field">
                    <label>${ke("common.device_type")}</label>
                    <select
                        .value=${this._type}
                        @change=${e=>this._type=e.target.value}
                    >
                        ${pa.map(e=>B`
                                <option
                                    value=${e.value}
                                    ?selected=${this._type===e.value}
                                >
                                    ${ke(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${e=>this._emitterIds=e.detail.value}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?ke("common.creating"):ke("promote.create_device")}
                    </button>
                </div>
            </ha-dialog>
        `}};ga.styles=[Bi,n`
        /* NOTE: no ha-textfield here anymore. This dialog was the
           panel's last ha-textfield user; the element is lazy-loaded by
           the HA frontend and is not reliably defined inside a custom
           panel, so it rendered as an empty, unfocusable shell (shampoo
           bench). The name box is now the shared .field + plain input,
           the same proven pattern as every other dialog. */
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ga.prototype,"api",void 0),e([pe({attribute:!1})],ga.prototype,"hass",void 0),e([pe()],ga.prototype,"suggestedName",void 0),e([ge()],ga.prototype,"_name",void 0),e([ge()],ga.prototype,"_type",void 0),e([ge()],ga.prototype,"_emitterIds",void 0),e([ge()],ga.prototype,"_busy",void 0),e([ge()],ga.prototype,"_error",void 0),ga=e([ue("ir-promote-dialog")],ga);let ma=class extends se{constructor(){super(...arguments),this.value=[],this.busy=!1,this._local=[]}connectedCallback(){super.connectedCallback(),this._local=[...this.value]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_send(){0!==this._local.length&&this.dispatchEvent(new CustomEvent("send",{detail:{emitters:[...this._local]},bubbles:!0,composed:!0}))}_onEmittersChanged(e){this._local=e.detail.value,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:this._local},bubbles:!0,composed:!0}))}render(){const e=this._local.length>0&&!this.busy;return B`
            <ha-dialog
                open
                heading=${ke("test_emitter.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._local}
                    ?disabled=${this.busy}
                    @emitters-changed=${this._onEmittersChanged}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this.busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn send-btn"
                        @click=${this._send}
                        ?disabled=${!e}
                    >
                        ${this.busy?ke("test_emitter.sending"):ke("test_emitter.send")}
                    </button>
                </div>
            </ha-dialog>
        `}};ma.styles=[Bi,n`
        /* Slimmer actions row than the shared one; ships this way. */
        .dialog-actions {
            margin-top: 16px;
            padding-top: 0;
            border-top: none;
        }
        /* Opacity in the transition so the Send hover fades, not snaps. */
        .action-btn {
            transition: background 150ms ease, opacity 150ms ease;
        }
        /* Brighter cancel than the shared secondary; ships this way. */
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .send-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .send-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ma.prototype,"api",void 0),e([pe({attribute:!1})],ma.prototype,"hass",void 0),e([pe({attribute:!1})],ma.prototype,"value",void 0),e([pe({type:Boolean})],ma.prototype,"busy",void 0),e([ge()],ma.prototype,"_local",void 0),ma=e([ue("ir-test-emitter-dialog")],ma);let ua=class extends se{constructor(){super(...arguments),this.assignments=[],this.top=0,this.left=0}render(){return B`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${ke("popover.assigned_to")}</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>${ke("popover.new_assignment")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.assignments.map(e=>B`
                        <button
                            class="popover-item"
                            title=${ke("popover.open_in_devices",{name:e.device_name})}
                            @click=${()=>this._emit("open-assignment",e)}
                        >
                            <span class="popover-name"
                                >${e.device_name} / ${e.command_name}</span
                            >
                            <ha-svg-icon
                                class="chevron"
                                .path=${"M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z"}
                            ></ha-svg-icon>
                        </button>
                    `)}
            </div>
        `}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};ua.styles=[Yi,n`
            :host {
                display: contents;
            }
            .chevron {
                --mdc-icon-size: 14px;
                color: var(--secondary-text-color);
                flex: none;
            }
        `],e([pe({attribute:!1})],ua.prototype,"assignments",void 0),e([pe({type:Number})],ua.prototype,"top",void 0),e([pe({type:Number})],ua.prototype,"left",void 0),ua=e([ue("ir-assigned-popover")],ua);const ha="hair-mirror";function _a(e,t){const i=e.decoded_fingerprint??null,a=t.decoded_fingerprint??null;if(null!==i&&null!==a)return i===a;const r=e.byte_hash??null,o=t.byte_hash??null;return null!==r&&null!==o?r===o:e.signal_fingerprint===t.fingerprint}var va;function ba(e){try{return new Date(e).toLocaleString(we(),{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function fa(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?ke("rel.just_now"):t<36e5?ke("rel.min_ago",{count:Math.floor(t/6e4)}):t<864e5?ke("rel.h_ago",{count:Math.floor(t/36e5)}):ke("rel.d_ago",{count:Math.floor(t/864e5)})}catch{return""}}const ya="M12 9.188c-1.553 0-2.812 1.259-2.812 2.812s1.259 2.812 2.812 2.812c1.553 0 2.812-1.259 2.812-2.812v0c-0.002-1.552-1.26-2.81-2.812-2.812h-0zM12 13.688c-0.932 0-1.688-0.755-1.688-1.688s0.755-1.688 1.688-1.688c0.932 0 1.688 0.755 1.688 1.688v0c-0.002 0.931-0.756 1.686-1.688 1.688h-0zM2.062 12c0.16-2.665 1.25-5.049 2.948-6.856l-0.005 0.006c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.393 0.16l0-0c-1.906 1.998-3.125 4.667-3.27 7.618l-0.001 0.028c0.146 2.979 1.365 5.647 3.275 7.652l-0.005-0.005c0.101 0.098 0.239 0.159 0.392 0.159 0.31 0 0.562-0.252 0.562-0.562 0-0.152-0.061-0.291-0.16-0.392l0 0c-1.694-1.8-2.785-4.185-2.94-6.821l-0.002-0.03zM6.647 12c0.113-1.859 0.874-3.523 2.058-4.784l-0.004 0.004c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.392 0.16l0-0c-1.39 1.457-2.278 3.403-2.383 5.554l-0.001 0.02c0.105 2.171 0.994 4.117 2.386 5.577l-0.003-0.004c0.102 0.104 0.244 0.167 0.4 0.167 0.31 0 0.562-0.251 0.562-0.562 0-0.156-0.064-0.297-0.167-0.399l-0-0c-1.183-1.256-1.944-2.92-2.053-4.759l-0.001-0.021zM19.793 4.355c-0.102-0.101-0.241-0.164-0.396-0.164-0.31 0-0.562 0.252-0.562 0.562 0 0.154 0.062 0.294 0.162 0.395l-0-0c1.691 1.802 2.782 4.185 2.94 6.82l0.002 0.03c-0.16 2.665-1.249 5.05-2.947 6.857l0.005-0.006c-0.105 0.102-0.17 0.244-0.17 0.403 0 0.31 0.252 0.562 0.562 0.562 0.158 0 0.301-0.065 0.404-0.171l0-0c1.906-1.999 3.125-4.667 3.268-7.618l0.001-0.028c-0.146-2.978-1.364-5.647-3.274-7.65l0.005 0.005zM15.299 6.425c-0.102 0.102-0.165 0.242-0.165 0.398 0 0.154 0.062 0.295 0.164 0.397l-0-0c1.181 1.257 1.942 2.92 2.054 4.758l0.001 0.022c-0.114 1.86-0.875 3.523-2.059 4.784l0.004-0.004c-0.101 0.102-0.164 0.241-0.164 0.396 0 0.311 0.252 0.563 0.563 0.563 0.155 0 0.295-0.062 0.397-0.164l-0 0c1.389-1.458 2.277-3.404 2.383-5.555l0.001-0.02c-0.105-2.172-0.994-4.118-2.388-5.578l0.003 0.003c-0.101-0.102-0.242-0.165-0.397-0.165s-0.295 0.063-0.397 0.165l-0 0z",wa="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let ka=va=class extends se{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._loading=!0,this._error=null,this._hasReceivers=!0,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._flashStats=new Set,this._recentSignalIds=[],this._glowSignalIds=new Set,this._hitFlashSignalIds=new Set,this._confirmClearAll=!1,this._triggers=[],this._triggerDialog=null,this._triggerEditDialog=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._editingDeviceId=null,this._editLabel="",this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._editSignal=null,this._testingSignalId=null,this._testResult=null,this._testDialog=null,this._testEmitters=[],this._dismissGlowActive=!1,this._dismissDotVisible=!1,this._unsubLive=null,this._unsubRemoved=null,this._unsubDismiss=null,this._dismissGlowTimer=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),a=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||a&&t.includes(a)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive(),this._subscribeRemoved(),this._subscribeDismissActivity(),this._subscribeUpdated()}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e&&(e.focus(),e.select())}this._syncSortables()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive(),this._unsubscribeRemoved(),this._unsubscribeDismissActivity(),this._unsubscribeUpdated(),this._removePopoverDismiss(),null!==this._dismissGlowTimer&&(clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=null),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(a,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[n]=o.splice(i,1);o.splice(a,0,n),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("sniffed",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`}},500)}async _load(){this._loading=!0;try{const[e,t,i,a]=await Promise.all([this.api.getUnknownDevices({include_dismissed:this._showDismissed,source:"sniffed"}),this.api.listDevices(),this.api.listTriggers(),this.api.getSnifferStatus()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._hasReceivers=a.has_receivers,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}async _subscribeRemoved(){try{this._unsubRemoved=await this.api.subscribeSignalRemoved(e=>{this._load(),this._expandedId===e.device_id&&(e.device_removed?(this._expandedId=null,this._expandedDevice=null):(this._toggleExpand(e.device_id),this._toggleExpand(e.device_id)))})}catch{}}async _unsubscribeRemoved(){this._unsubRemoved&&(await this._unsubRemoved(),this._unsubRemoved=null)}async _subscribeDismissActivity(){try{this._unsubDismiss=await this.api.subscribeDismissActivity(()=>this._onDismissActivity())}catch{}}async _unsubscribeDismissActivity(){this._unsubDismiss&&(await this._unsubDismiss(),this._unsubDismiss=null)}_onDismissActivity(){this._dismissDotVisible=!0,this._dismissGlowActive=!0,null!==this._dismissGlowTimer&&clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=setTimeout(()=>{this._dismissGlowActive=!1,this._dismissGlowTimer=null},va.DISMISS_GLOW_HOLD_MS)}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??e.protocol??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),a=this._devices.findIndex(t=>t.id===e);if(a>=0){const e=[...this._devices];e[a]={...e[a],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_cancelRename(){this._editingDeviceId=null}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&this._cancelRename()}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}_closePromote(){this._promoteTarget=null}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i,a){this._assignSignal={deviceId:e,signal:t,label:i??null,initialMode:a??"existing"}}_onAssignClick(e,t,i,a){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=a?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}_closeAssign(){this._assignSignal=null}async _onSignalAssigned(e){if(this._assignSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}_closeDelete(){this._deleteSignal=null}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){if(this._editSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}_closeTestDialog(){this._testDialog=null}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,a=i.length;this._testResult=e===a?1===a?ke("mirror.sent"):ke("mirror.sent_all_n",{sent:e,total:a}):0===e?ke("mirror.failed"):`Sent (${e}/${a})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_a(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_a(t,e)).length}_openTriggerDialog(e,t,i){const a=this._triggers.filter(e=>_a(e,t));if(0===a.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_onLiveSignal(e){if(e.device_fingerprint===ha)return;const t=(new Date).toISOString(),i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){{const a={...this._devices[i]};a.hit_count=e.device_hit_count??e.hit_count,a.last_seen=t,1===e.hit_count&&(a.signal_count=(a.signal_count??0)+1);const r=[...this._devices];r[i]=a,this._devices=r}if(this._expandedDevice&&this._expandedId===e.device_id){const i=this._expandedDevice.signals.findIndex(t=>t.id===e.signal_id);if(i>=0){const a={...this._expandedDevice.signals[i]};a.hit_count=e.hit_count,a.last_seen=t;const r=[...this._expandedDevice.signals];r[i]=a,this._expandedDevice={...this._expandedDevice,hit_count:e.device_hit_count??e.hit_count,last_seen:t,signals:r}}else this.api.getUnknownDevice(e.device_id).then(t=>{if(this._expandedId===e.device_id){this._expandedDevice=t;const i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){const e={...this._devices[i],signal_count:t.signals.length},a=[...this._devices];a[i]=e,this._devices=a}}}).catch(()=>{})}if(this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800),this._flashStats=new Set([...this._flashStats,e.device_id]),setTimeout(()=>{const t=new Set(this._flashStats);t.delete(e.device_id),this._flashStats=t},1500),e.signal_id){const t=[e.signal_id,...this._recentSignalIds.filter(t=>t!==e.signal_id)].slice(0,2);this._recentSignalIds=t,this._glowSignalIds=new Set([...this._glowSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._glowSignalIds);t.delete(e.signal_id),this._glowSignalIds=t},1200),this._hitFlashSignalIds=new Set([...this._hitFlashSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._hitFlashSignalIds);t.delete(e.signal_id),this._hitFlashSignalIds=t},1200)}}else this._load()}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._dismissDotVisible=!1,this._load()}render(){return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ya}></ha-svg-icon>
                    ${ke("sniffer.title")}
                    ${this._loading?"":B`<span class="count"
                              >(${$e("sniffer.remotes",this._devices.length)})</span
                          >`}
                </span>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">${ke("sniffer.scanning")}</div>`:0===this._devices.length?this._hasReceivers?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ya}></ha-svg-icon>
                            <h3>${ke("sniffer.empty_title")}</h3>
                            <p>${ke("sniffer.empty_body")}</p>
                            <p class="hint">${ke("sniffer.empty_hint")}</p>
                        </ha-card>
                    `:B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ya}></ha-svg-icon>
                            <h3>${ke("sniffer.norx_title")}</h3>
                            <p>${ke("sniffer.norx_body")}</p>
                            <p class="hint">${ke("sniffer.norx_hint")}</p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${He(this._remotesVersion,Me(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            <div class="bottom-bar">
                <button
                    class="action-btn dismiss-btn ${this._dismissGlowActive?"dismiss-glow":""}"
                    title=${ke("sniffer.show_dismissed_title")}
                    @click=${this._toggleDismissed}
                >
                    ${this._showDismissed?ke("sniffer.hide_dismissed"):ke("sniffer.show_dismissed")}
                    ${this._dismissDotVisible?B`<span class="dismiss-dot" aria-hidden="true"></span>`:""}
                </button>
                ${this._devices.length>0||this._showDismissed?B`<button
                          class="action-btn delete-btn"
                          title=${ke("sniffer.clear_all_title")}
                          @click=${()=>this._confirmClearAll=!0}
                      >
                          ${ke("sniffer.clear_all")}
                      </button>`:""}
            </div>

            ${this._assignSignal?B`
                      <ir-assign-signal-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .unknownDeviceId=${this._assignSignal.deviceId}
                          .signal=${this._assignSignal.signal}
                          .suggestedDeviceName=${this._assignSignal.label??""}
                          .initialMode=${this._assignSignal.initialMode}
                          @signal-assigned=${this._onSignalAssigned}
                          @closed=${this._closeAssign}
                      ></ir-assign-signal-dialog>
                  `:""}

            ${this._promoteTarget?B`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .suggestedName=${this._promoteTarget.label??""}
                          @device-created=${this._onDevicePromoted}
                          @closed=${this._closePromote}
                      ></ir-promote-dialog>
                  `:""}

            ${this._deleteSignal?B`
                      <ir-confirm-dialog
                          title=${ke("sniffer.del_signal_title")}
                          message=${ke("sniffer.del_signal_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._editSignal?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .allowSnap=${!0}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._confirmClearAll?B`
                      <ir-confirm-dialog
                          title=${ke("sniffer.clear_all_confirm_title")}
                          message=${ke("sniffer.clear_all_confirm_msg")}
                          confirmLabel="Clear All"
                          .destructive=${!0}
                          @confirmed=${this._doClearAll}
                          @closed=${()=>this._confirmClearAll=!1}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._triggerPopover?B`
                      <ir-trigger-popover
                          .triggers=${this._triggers.filter(e=>_a(e,this._triggerPopover.signal))}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onPopoverCreateNew}
                          @edit-trigger=${this._onPopoverEditTrigger}
                      ></ir-trigger-popover>
                  `:""}
            ${this._assignedPopover?B`
                      <ir-assigned-popover
                          .assignments=${this._assignedPopover.signal.assigned_to??[]}
                          .top=${this._assignedPopover.top}
                          .left=${this._assignedPopover.left}
                          @create-new=${this._onAssignedPopoverCreateNew}
                          @open-assignment=${this._onAssignedPopoverOpen}
                      ></ir-assigned-popover>
                  `:""}
            ${this._triggerDialog?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                          .byteHash=${this._triggerDialog.signal.byte_hash??null}
                          .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                          .protocol=${this._triggerDialog.signal.protocol}
                          .code=${this._triggerDialog.signal.code}
                          .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                          .alias=${this._triggerDialog.signal.alias||null}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._testDialog?B`
                      <ir-test-emitter-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .value=${this._testEmitters}
                          @emitters-changed=${e=>this._testEmitters=e.detail.value}
                          @send=${this._sendTest}
                          @closed=${this._closeTestDialog}
                      ></ir-test-emitter-dialog>
                  `:""}
            ${this._triggerEditDialog?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEditDialog}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?B`
                      <ir-confirm-dialog
                          title=${ke("mirror.del_trigger_title")}
                          message=${ke("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id),a=this._flashStats.has(e.id);return B`
            <ha-card class="device ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row ${i?"flash-row":""}"
                    @click=${()=>this._toggleExpand(e.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${wa}
                                          title=${ke("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      ${e.dismissed?B`<span class="protocol locked"
                                                >${e.label??e.protocol??ke("common.raw")}</span
                                            >`:B`<span
                                                class="protocol"
                                                title=${ke("cmdrow.rename")}
                                                @click=${t=>this._startRename(e,t)}
                                            >${e.label??e.protocol??ke("common.raw")}</span>`}`}
                            <span class="device-stats ${a?"stats-flash":""}">
                                <span class="stat"
                                    ><strong>${e.hit_count}</strong>
                                    ${$e("sniffer.hit_word",e.hit_count)}</span
                                >
                                <span class="stat"
                                    ><strong>${e.signal_count}</strong>
                                    ${$e("sniffer.signal_word",e.signal_count)}</span
                                >
                                <span class="stat last-seen" title=${ba(e.last_seen)}>${fa(e.last_seen)}</span>
                            </span>
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >${ke("sniffer.hair_device")}</span>`:e.label&&!e.dismissed?B`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >${ke("sniffer.promote")}</span>`:""}
                            ${e.device_address?B`<span class="address">${ke("sniffer.addr",{address:e.device_address})}</span>`:""}
                            ${e.dismissed?B`<span class="dismissed-badge">${ke("sniffer.dismissed")}</span>`:""}
                        </div>
                    </div>
                    ${e.dismissed?B`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._undismiss(e.id)}}
                          >${ke("sniffer.restore")}</button>`:B`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._dismiss(e.id)}}
                          >${ke("sniffer.dismiss")}</button>`}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>${ke("sniffer.signals_head",{count:e.signals.length})}</span>
                    <span class="first-seen">${ke("sniffer.first_seen",{time:ba(e.first_seen)})}</span>
                </div>
                <div class="signal-list">
                    ${He(this._signalsVersion,Me(e.signals,e=>e.id,t=>{const i=this._recentSignalIds.indexOf(t.id),a=0===i,r=1===i,o=this._glowSignalIds.has(t.id),n=this._hitFlashSignalIds.has(t.id);return B`
                            <div class="signal-row">
                                ${e.dismissed?"":B`<ha-svg-icon
                                          class="signal-grip"
                                          .path=${wa}
                                          title=${ke("devdetail.drag")}
                                      ></ha-svg-icon>`}
                                <div class="signal-info">
                                    <ir-signal-alias
                                        .api=${this.api}
                                        .deviceId=${e.id}
                                        .signal=${t}
                                        ?disabled=${e.dismissed}
                                        @alias-changed=${this._onAliasChanged}
                                    ></ir-signal-alias>
                                </div>
                                <div class="signal-meta">
                                    <span class="${n?"hit-flash":""}"
                                        >${t.hit_count}
                                        ${$e("sniffer.hit_word",t.hit_count)}</span
                                    >
                                    <span title=${ba(t.last_seen)}
                                        >${fa(t.last_seen)}</span
                                    >
                                    <span>${Math.round(t.frequency/1e3)} kHz</span>
                                </div>
                                ${t.code?B`<button
                                          ?disabled=${e.dismissed}
                                          title=${ke("cmdrow.edit_code")}
                                          @click=${i=>this._openEditSignal(e.id,t,i)}
                                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                                      >
                                          <ha-svg-icon
                                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                              style="--mdc-icon-size:10px"
                                          ></ha-svg-icon>
                                      </button>`:""}
                                <div class="signal-actions">
                                    <button
                                        class="action-btn assign-btn ${a?"recent-latest":""} ${r?"recent-previous":""} ${o?"glow":""}"
                                        @click=${i=>{i.stopPropagation(),this._onAssignClick(e.id,t,e.label,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?ke("mirror.assigned_one",{device:t.assigned_to[0].device_name,command:t.assigned_to[0].command_name}):ke("mirror.assigned_n",{count:t.assignment_count})+`\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:e.dismissed?ke("sniffer.restore_first"):ke("mirror.assign_title")}
                                    >${ke("assign.assign")}<ir-count-dot
                                            color="green"
                                            .count=${t.assignment_count??0}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                                        ?disabled=${e.dismissed||this._testingSignalId===t.id}
                                        title=${e.dismissed?ke("sniffer.restore_first"):ke("mirror.test_title")}
                                    >${this._testingSignalId===t.id?this._testResult??ke("mirror.sending"):ke("mirror.test")}</button>
                                    <button
                                        class="action-btn trigger-btn"
                                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e.id,t,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${this._hasTrigger(t)?ke("mirror.trigger_edit"):e.dismissed?ke("sniffer.restore_first"):ke("sniffer.trigger_create")}
                                    >${ke("cmdrow.trigger")}<ir-count-dot
                                            color="yellow"
                                            .count=${this._triggerCountFor(t)}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${i=>{i.stopPropagation(),this._openDelete(e.id,t)}}
                                    >${ke("common.delete")}</button>
                                </div>
                            </div>
                        `}))}
                </div>
            </div>
        `}};ka.DISMISS_GLOW_HOLD_MS=3800,ka.styles=[Li,n`
        :host {
            display: block;
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--primary-color);
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
        }

        /* Clear All anchor below the unknown-devices list.
           Moved out of the top toolbar in v0.2.1 to pair visually with
           the new "Clear All also wipes the dismiss list" semantic, and
           to force the user to scroll past what they are about to delete
           before pressing the destructive button. */
        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        /* Show Dismissed stacked above Clear All, both right-aligned. */
        .bottom-bar {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            margin-top: 16px;
        }

        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: var(--disabled-text-color);
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .device {
            transition: box-shadow 200ms ease;
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so it does not poke past the border stroke. */
            overflow: hidden;
            /* Subtle stroke in the Sniffer's accent blue (the radio-icon
               colour) at the same 0.3 as the Clips copper stroke. The
               rgba line is a fallback for webviews without color-mix. */
            border: 1px solid rgba(33, 150, 243, 0.3);
            border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
        }
        /* Hit flash: pulse the device-row background. When the card is
           collapsed the row fills the whole card (the card's overflow:hidden
           clips the pulse to the rounded corners), so the entire card appears
           to flash; when expanded only the top row flashes, leaving the signal
           list below calm. */
        .device-row.flash-row {
            animation: row-flash 900ms ease-out;
        }
        @keyframes row-flash {
            0% { background: transparent; }
            18% {
                background: rgba(33, 150, 243, 0.32);
                background: color-mix(in srgb, var(--primary-color) 32%, transparent);
            }
            100% { background: transparent; }
        }
        .device.dismissed {
            opacity: 0.6;
        }

        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .device-icon {
            --mdc-icon-size: 16px;
            color: var(--primary-color);
            flex-shrink: 0;
        }
        /* Remote drag handle (replaces the radio icon): blue, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: var(--primary-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        /* Signal drag handle: gray, same as the hits / time / frequency meta. */
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        /* SortableJS marks the element being dragged. */
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol:not(.locked):hover {
            border-bottom-color: var(--primary-color);
        }
        .protocol.locked {
            cursor: default;
        }
        .edit-icon {
            --mdc-icon-size: 14px;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.4;
            transition: opacity 150ms ease;
        }
        .device-header:hover .edit-icon {
            opacity: 0.8;
        }
        .edit-icon:hover {
            opacity: 1 !important;
            color: var(--primary-color);
        }
        /* Identical box to .promote-badge (now also uppercase, so no
           line-height hack needed) -- only the colour differs. */
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
            margin-left: 4px;
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            margin-left: 4px;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
            flex-shrink: 0;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 140px;
        }
        .address {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: monospace;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .device-stats {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }

        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .first-seen {
            color: var(--secondary-text-color);
            font-weight: 400;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            /* Match the page background so the Sniffer signal rows blend
               with the panel backdrop instead of reading as highlighted
               peach strips, mirroring the device-detail command row
               treatment. Device-row hover (above) and action-btn hover
               (below) still use --secondary-background-color so hover
               feedback stays distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        /* Mobile layout fix.
           On narrow viewports the diamond pattern inside .signal-info
           wraps internally into a tall column, and flex/align-center
           floats the action buttons (Assign / Test / Trigger / Delete)
           into the vertical middle of the row with huge whitespace
           above and below. Switching to a 2-row grid keeps the
           diamonds + meta on the first row and stacks the action
           buttons below in their own band. Mirrors the bounded row
           height that the device-detail command rows already get via
           their fixed-column grid on every viewport. */
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }

        /* Transient blue pulse on the Show Dismissed button when a
           signal arrives from a remote in the dismiss set. Reuses the
           same --primary-color blue users associate with "a signal just
           arrived", held ~3.8s so it sits about 1.3s longer than the
           hit-flash and stays discoverable. */
        .action-btn.dismiss-btn.dismiss-glow {
            animation: dismiss-pulse 3.8s ease-out;
            border-color: var(--primary-color);
        }
        @keyframes dismiss-pulse {
            0% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
            12% { box-shadow: 0 0 10px 3px rgba(33, 150, 243, 0.55); }
            70% { box-shadow: 0 0 6px 2px rgba(33, 150, 243, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
        }

        /* Persistent dot indicator anchored to the top-right of the
           Show Dismissed button. Stays visible from the first
           dismiss-activity event after panel mount until the user
           clicks the button (the natural click-through that owns
           restoring dismissed remotes). */
        .dismiss-dot {
            position: absolute;
            top: -3px;
            right: -3px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary-color);
            box-shadow: 0 0 4px rgba(33, 150, 243, 0.55);
            pointer-events: none;
        }

        /* Latest signal: deep green fill (AA contrast with the white
           label) with a mint rim that previews the hit ring. Locked
           design: sniffer-hit-glow.md -- the earlier same-green halo
           read as a blob against the fill. */
        .action-btn.assign-btn.recent-latest {
            color: #fff;
            background: #2e7d32;
            border-color: #69f0ae;
        }
        .action-btn.assign-btn.recent-latest:hover {
            background: #1b5e20;
        }

        /* Previous signal: muted green outline Assign button */
        .action-btn.assign-btn.recent-previous {
            color: rgba(46, 125, 50, 0.6);
            border-color: rgba(46, 125, 50, 0.25);
            background: rgba(46, 125, 50, 0.06);
        }
        .action-btn.assign-btn.recent-previous:hover {
            background: rgba(46, 125, 50, 0.12);
        }

        /* Hit pulse: the mint rim blooms into a ring, brighter than
           the fill so the halo separates instead of blobbing. */
        .action-btn.assign-btn.glow {
            animation: assign-glow 1.4s ease-out;
        }
        @keyframes assign-glow {
            0% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0.9); }
            35% { box-shadow: 0 0 0 2px #69f0ae, 0 0 12px 5px rgba(105, 240, 174, 0.55); }
            100% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0); }
        }

        /* Hit count flash animation */
        .signal-meta .hit-flash {
            animation: hit-count-glow 1.2s ease-out;
        }
        @keyframes hit-count-glow {
            0% { color: #2e7d32; text-shadow: 0 0 6px rgba(46, 125, 50, 0.8); }
            100% { color: inherit; text-shadow: none; }
        }

        /* Collapsed stats flash on hit */
        .device-stats.stats-flash strong {
            color: var(--primary-color);
            transition: color 300ms ease;
        }
    `],e([pe({attribute:!1})],ka.prototype,"api",void 0),e([pe({attribute:!1})],ka.prototype,"hass",void 0),e([ge()],ka.prototype,"_devices",void 0),e([ge()],ka.prototype,"_hairDevices",void 0),e([ge()],ka.prototype,"_loading",void 0),e([ge()],ka.prototype,"_error",void 0),e([ge()],ka.prototype,"_hasReceivers",void 0),e([ge()],ka.prototype,"_showDismissed",void 0),e([ge()],ka.prototype,"_expandedId",void 0),e([ge()],ka.prototype,"_expandedDevice",void 0),e([ge()],ka.prototype,"_flashIds",void 0),e([ge()],ka.prototype,"_flashStats",void 0),e([ge()],ka.prototype,"_recentSignalIds",void 0),e([ge()],ka.prototype,"_glowSignalIds",void 0),e([ge()],ka.prototype,"_hitFlashSignalIds",void 0),e([ge()],ka.prototype,"_confirmClearAll",void 0),e([ge()],ka.prototype,"_triggers",void 0),e([ge()],ka.prototype,"_triggerDialog",void 0),e([ge()],ka.prototype,"_triggerEditDialog",void 0),e([ge()],ka.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],ka.prototype,"_triggerPopover",void 0),e([ge()],ka.prototype,"_assignedPopover",void 0),e([ge()],ka.prototype,"_receivers",void 0),e([ge()],ka.prototype,"_editingDeviceId",void 0),e([ge()],ka.prototype,"_editLabel",void 0),e([ge()],ka.prototype,"_promoteTarget",void 0),e([ge()],ka.prototype,"_assignSignal",void 0),e([ge()],ka.prototype,"_deleteSignal",void 0),e([ge()],ka.prototype,"_editSignal",void 0),e([ge()],ka.prototype,"_testingSignalId",void 0),e([ge()],ka.prototype,"_testResult",void 0),e([ge()],ka.prototype,"_testDialog",void 0),e([ge()],ka.prototype,"_testEmitters",void 0),e([ge()],ka.prototype,"_dismissGlowActive",void 0),e([ge()],ka.prototype,"_dismissDotVisible",void 0),e([ge()],ka.prototype,"_remotesVersion",void 0),e([ge()],ka.prototype,"_signalsVersion",void 0),ka=va=e([ue("ir-signal-monitor")],ka);let xa=class extends se{constructor(){super(...arguments),this._name="",this._busy=!1,this._error=null,this._brands=[],this._selectedBrand="",this._selectedCodebook="",this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadBrands()}async _loadBrands(){try{this._brands=await this.api.getCodeBrands()}catch{this._brands=[]}}_brand(e){return this._brands.find(t=>t.brand===e)}_codebookLabel(e,t){const i=this._brand(e)?.codebooks.find(e=>e.id===t);return i?.label??""}_maybeAutofillName(){if(this._nameEdited)return;const e=this._brand(this._selectedBrand);if(!e||!this._selectedCodebook)return;const t=this._codebookLabel(this._selectedBrand,this._selectedCodebook);this._name=`${e.label} ${t}`.trim()}_onBrandChange(e){this._selectedBrand=e.target.value;const t=this._brand(this._selectedBrand);t&&1===t.codebooks.length?this._selectedCodebook=t.codebooks[0].id:this._selectedCodebook="",this._maybeAutofillName()}_onCodebookChange(e){this._selectedCodebook=e.target.value,this._maybeAutofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim()){this._busy=!0,this._error=null;try{let e;e=this._selectedCodebook?(await this.api.importCodeRemote(this._selectedCodebook,this._name.trim())).device:await this.api.createRemote(this._name.trim()),this.dispatchEvent(new CustomEvent("remote-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("common.name_required")}_onKeydown(e){"Enter"===e.key&&this._create()}render(){const e=this._brand(this._selectedBrand);return B`
            <ha-dialog
                open
                heading=${ke("createremote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${ke("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${ke("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>{this._name=e.target.value,this._nameEdited=!0}}
                        @keydown=${this._onKeydown}
                    />
                </div>

                ${this._brands.length>0?B`
                          <div class="field">
                              <label>${ke("createremote.type")}</label>
                              <select
                                  .value=${this._selectedBrand}
                                  @change=${this._onBrandChange}
                              >
                                  <option value="">${ke("createremote.blank")}</option>
                                  <optgroup label=${ke("createremote.from_library")}>
                                      ${this._brands.map(e=>B`<option value=${e.brand}>
                                              ${e.label}
                                          </option>`)}
                                  </optgroup>
                              </select>
                          </div>

                          ${e?B`<div class="field">
                                    <label>${ke("createremote.model")}</label>
                                    <select
                                        .value=${this._selectedCodebook}
                                        @change=${this._onCodebookChange}
                                    >
                                        <option value="">
                                            ${ke("createremote.select_model")}
                                        </option>
                                        ${e.codebooks.map(e=>B`<option value=${e.id}>
                                                ${e.label}
                                                (${e.functions.length})
                                            </option>`)}
                                    </select>
                                </div>`:""}
                      `:""}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?ke("common.creating"):ke("adddev.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};xa.styles=[Bi,n`
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #b87333;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],xa.prototype,"api",void 0),e([ge()],xa.prototype,"_name",void 0),e([ge()],xa.prototype,"_busy",void 0),e([ge()],xa.prototype,"_error",void 0),e([ge()],xa.prototype,"_brands",void 0),e([ge()],xa.prototype,"_selectedBrand",void 0),e([ge()],xa.prototype,"_selectedCodebook",void 0),xa=e([ue("ir-create-remote-dialog")],xa);const $a="M12.462,10.448c-0.639-0.639-1.678-0.639-2.317,0c-0.639,0.639-0.639,1.678,0,2.317l1.09,1.09c0.319,0.319,0.739,0.479,1.159,0.479c0.42,0,0.839-0.16,1.159-0.479c0-0,0-0,0-0c0.639-0.639,0.639-1.678,0-2.317L12.462,10.448z M12.763,13.066c-0.204,0.204-0.535,0.204-0.739,0l-1.09-1.09c-0.204-0.204-0.204-0.535,0-0.739c0.102-0.102,0.236-0.153,0.369-0.153c0.134,0,0.267,0.051,0.369,0.153l1.09,1.09C12.966,12.531,12.966,12.863,12.763,13.066z M23.998,6.609l-0.104-1.419c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.068-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-1.419-0.103c-0.162-0.012-0.321,0.047-0.435,0.162l-1.993,1.993c-0,0.001-0.001,0.001-0.001,0.001c-0.097,0.097-0.191,0.197-0.282,0.298c-1.933,2.042-12.871,13.598-13.716,14.551c-0.722,0.814-0.712,1.983,0.023,2.717l0.341,0.341L0.539,20.852c-0.719,0.719-0.719,1.889,0,2.609c0.36,0.36,0.832,0.539,1.304,0.539c0.472,0,0.945-0.18,1.304-0.539l0.787-0.787l0.341,0.341c0.735,0.735,1.903,0.745,2.717,0.023c0.953-0.845,12.509-11.783,14.551-13.716c0.102-0.091,0.201-0.186,0.299-0.283c0.001-0.001,0.001-0.001,0.001-0.002l1.992-1.992C23.951,6.93,24.01,6.771,23.998,6.609z M20.61,4.179l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.734L20.61,4.179z M19.087,2.656l0.684,0.05l0.05,0.684L18.403,4.807L17.67,4.074L19.087,2.656z M17.564,1.133l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.733L17.564,1.133z M2.359,22.671c-0.284,0.284-0.746,0.284-1.03,0c-0.284-0.284-0.284-0.746,0-1.03l0.787-0.787l1.03,1.03L2.359,22.671z M6.253,22.202c-0.366,0.324-0.877,0.334-1.188,0.023l-0.735-0.735l-2.555-2.555c-0.311-0.311-0.301-0.822,0.023-1.188c0.633-0.715,7.3-7.769,11.189-11.88c-0.014,0.084-0.026,0.169-0.036,0.253c-0.179,1.482,0.239,2.815,1.176,3.752c0.937,0.937,2.27,1.355,3.752,1.176c0.084-0.01,0.169-0.022,0.253-0.036C14.022,14.901,6.968,21.568,6.253,22.202z M14.917,9.083c-0.69-0.69-0.994-1.694-0.857-2.829c0.123-1.019,0.585-2.03,1.315-2.897l0.717,0.717l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.717,0.717C18.756,10.213,16.277,10.443,14.917,9.083z M21.449,7.853l-0.734-0.734l1.418-1.418l0.684,0.05l0.05,0.684L21.449,7.853z",Sa="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let Ca=class extends se{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._createSignalDeviceId=null,this._editSignal=null,this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),a=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||a&&t.includes(a)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(a,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[n]=o.splice(i,1);o.splice(a,0,n),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("manual",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!0,min_hits:0,source:"manual"}),this.api.listDevices(),this.api.listTriggers()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onRemoteCreated(e){this._createRemoteOpen=!1,await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openCreateSignal(e,t){t.stopPropagation(),this._createSignalDeviceId=e}async _onSignalCreated(){this._createSignalDeviceId=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this remote",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deleteRemote(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),a=this._devices.findIndex(t=>t.id===e);if(a>=0){const e=[...this._devices];e[a]={...e[a],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,a){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=a?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,a=i.length;this._testResult=e===a?1===a?ke("mirror.sent"):ke("mirror.sent_all_n",{sent:e,total:a}):0===e?ke("mirror.failed"):`Sent (${e}/${a})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_a(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_a(t,e)).length}_openTriggerDialog(e,t,i){const a=this._triggers.filter(e=>_a(e,t));if(0===a.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("manual"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}render(){const e=this._devices.length;return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${$a}></ha-svg-icon>
                    ${ke("clips.title")}
                    ${this._loading?"":B`<span class="count"
                              >(${$e("sniffer.remotes",e)})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        ${ke("clips.add_remote")}
                    </button>
                </div>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">${ke("common.loading_plain")}</div>`:0===e?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${$a}></ha-svg-icon>
                            <h3>${ke("clips.empty_title")}</h3>
                            <p>${ke("clips.empty_body")}</p>
                            <p class="hint">${ke("clips.empty_hint")}</p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${He(this._remotesVersion,Me(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?B`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title=${ke("clips.clear_all_title")}
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              ${ke("sniffer.clear_all")}
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return B`
            <ha-card class="device clip-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${Sa}
                                          title=${ke("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title=${ke("cmdrow.rename")}
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??ke("clips.remote_fallback")}</span
                                      >`}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${$e("sniffer.signal_word",e.signal_count)}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >${ke("sniffer.hair_device")}</span>`:e.label?B`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >${ke("sniffer.promote")}</span>`:""}
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>${ke("sniffer.signals_head",{count:e.signals.length})}</span>
                    <button
                        class="create-signal-btn"
                        title=${ke("clips.add_signal_title")}
                        @click=${t=>this._openCreateSignal(e.id,t)}
                    >
                        ${ke("clips.add_signal")}
                    </button>
                </div>
                ${0===e.signals.length?B`<div class="no-signals-row">
                          <span class="no-signals"
                              >${ke("clips.no_signals")}</span
                          >
                      </div>`:B`
                          <div class="signal-list">
                              ${He(this._signalsVersion,Me(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title=${ke("clips.delete_remote_title")}
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >${ke("clips.delete_remote")}</button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const a=this._testingSignalId===t.id;return B`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${Sa}
                    title=${ke("devdetail.drag")}
                ></ha-svg-icon>
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${e}
                        .signal=${t}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${e=>this._error=e.detail}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${a&&this._testResult?B`<span class="test-result">${this._testResult}</span>`:B`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?B`<button
                          title=${ke("cmdrow.edit_code")}
                          @click=${i=>this._openEditSignal(e,t,i)}
                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                      >
                          <ha-svg-icon
                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                              style="--mdc-icon-size:10px"
                          ></ha-svg-icon>
                      </button>`:""}
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:ke("mirror.assign_title")}
                        @click=${a=>{a.stopPropagation(),this._onAssignClick(e,t,i,a)}}
                    >${ke("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${a}
                        title=${ke("clips.test_title")}
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >${a?this._testResult??ke("mirror.sending"):ke("mirror.test")}</button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?ke("mirror.trigger_edit"):ke("sniffer.trigger_create")}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >${ke("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >${ke("common.delete")}</button>
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._createRemoteOpen?B`<ir-create-remote-dialog
                      .api=${this.api}
                      @remote-created=${this._onRemoteCreated}
                      @closed=${()=>this._createRemoteOpen=!1}
                  ></ir-create-remote-dialog>`:""}

            ${this._createSignalDeviceId?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._createSignalDeviceId}
                      @signal-created=${this._onSignalCreated}
                      @closed=${()=>this._createSignalDeviceId=null}
                  ></ir-signal-editor>`:""}

            ${this._editSignal?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .hasTrigger=${this._hasTrigger(this._editSignal.signal)}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._assignSignal?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._promoteTarget?B`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._deleteSignal?B`<ir-confirm-dialog
                      title=${ke("sniffer.del_signal_title")}
                      message=${ke("sniffer.del_signal_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?B`<ir-confirm-dialog
                      title=${ke("clips.clear_all_confirm_title")}
                      message=${ke("clips.clear_all_confirm_msg")}
                      confirmLabel=${ke("sniffer.clear_all")}
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?B`<ir-confirm-dialog
                      title=${ke("clips.del_remote_confirm_title")}
                      message=${this._deleteRemoteCount>0?$e("clips.del_remote_msg_n",this._deleteRemoteCount,{name:this._deleteRemoteLabel??""}):ke("clips.del_remote_msg",{name:this._deleteRemoteLabel??""})}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_a(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .byteHash=${this._triggerDialog.signal.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                      .alias=${this._triggerDialog.signal.alias||null}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}

            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title=${ke("mirror.del_trigger_title")}
                      message=${ke("devdetail.del_trigger_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};Ca.styles=[Li,n`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: #b87333;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        /* Header "+ Create" -- sized to match the Hide Dismissed (action-btn)
           button beside it: same padding/font, copper colors. */
        /* Toolbar "+ Add Remote": shared chip anatomy, copper accent. */
        .action-btn.create-btn {
            color: #b87333;
            border-color: #b87333;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        /* Card-internal "+ Add Signal": borderless copper text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Remote accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 10px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #b87333;
            cursor: pointer;
        }
        .create-signal-btn:hover:not(:disabled) {
            background: none;
            text-decoration: underline;
        }

        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        /* Show Dismissed stacked above Clear All, both right-aligned. */
        .bottom-bar {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            margin-top: 16px;
        }
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #b87333;
            opacity: 0.5;
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .device.clip-device {
            border: 1px solid rgba(184, 115, 51, 0.3);
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so its square corners do not poke out over
               the border stroke. */
            overflow: hidden;
        }
        .device.dismissed {
            opacity: 0.6;
        }
        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .clip-icon {
            --mdc-icon-size: 14px;
            color: #b87333;
        }
        /* Remote drag handle (replaces the paperclip): copper, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #b87333;
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        /* Signal drag handle: gray, same as the hits / time / frequency meta. */
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        /* SortableJS marks the element being dragged. */
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:not(.locked):hover {
            border-bottom-color: #b87333;
        }
        .protocol.locked {
            cursor: default;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .stat {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
            flex-shrink: 0;
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }

        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        /* "+ Create" sits immediately right of the "Signals (N)" label,
           left-aligned, rather than pushed to the far right. */
        .signal-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .no-signals-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        /* Persistent "Delete remote" footer: a row below the signal list,
           right-justified so its button lines up with the per-signal Delete
           buttons (which sit 8px in from the row edge). Same button size as
           every other action button. */
        .remote-footer {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
            padding-right: 8px;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .test-result {
            color: #2e7d32;
            font-weight: 500;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
    `],e([pe({attribute:!1})],Ca.prototype,"api",void 0),e([pe({attribute:!1})],Ca.prototype,"hass",void 0),e([ge()],Ca.prototype,"_devices",void 0),e([ge()],Ca.prototype,"_hairDevices",void 0),e([ge()],Ca.prototype,"_triggers",void 0),e([ge()],Ca.prototype,"_loading",void 0),e([ge()],Ca.prototype,"_error",void 0),e([ge()],Ca.prototype,"_expandedId",void 0),e([ge()],Ca.prototype,"_expandedDevice",void 0),e([ge()],Ca.prototype,"_confirmClearAll",void 0),e([ge()],Ca.prototype,"_deleteRemoteId",void 0),e([ge()],Ca.prototype,"_deleteRemoteLabel",void 0),e([ge()],Ca.prototype,"_deleteRemoteCount",void 0),e([ge()],Ca.prototype,"_editingDeviceId",void 0),e([ge()],Ca.prototype,"_editLabel",void 0),e([ge()],Ca.prototype,"_createRemoteOpen",void 0),e([ge()],Ca.prototype,"_createSignalDeviceId",void 0),e([ge()],Ca.prototype,"_editSignal",void 0),e([ge()],Ca.prototype,"_promoteTarget",void 0),e([ge()],Ca.prototype,"_assignSignal",void 0),e([ge()],Ca.prototype,"_deleteSignal",void 0),e([ge()],Ca.prototype,"_triggerDialog",void 0),e([ge()],Ca.prototype,"_triggerEditDialog",void 0),e([ge()],Ca.prototype,"_triggerPopover",void 0),e([ge()],Ca.prototype,"_assignedPopover",void 0),e([ge()],Ca.prototype,"_receivers",void 0),e([ge()],Ca.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],Ca.prototype,"_testDialog",void 0),e([ge()],Ca.prototype,"_testEmitters",void 0),e([ge()],Ca.prototype,"_testingSignalId",void 0),e([ge()],Ca.prototype,"_testResult",void 0),e([ge()],Ca.prototype,"_remotesVersion",void 0),e([ge()],Ca.prototype,"_signalsVersion",void 0),Ca=e([ue("ir-clips")],Ca);let Aa=class extends se{constructor(){super(...arguments),this.pendingEntity="",this._candidates=[],this._entityId="",this._appliance="",this._name="",this._busy=!1,this._loading=!0,this._error=null,this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadVendors()}async _loadVendors(){this._loading=!0;try{const{vendors:e}=await this.api.listPluckVendors();this._candidates=this._flatten(e);const t=this._candidates.find(e=>e.entityId===this.pendingEntity)??(1===this._candidates.length?this._candidates[0]:void 0);t&&(this._entityId=t.entityId,this._autofillName())}catch(e){this._error=e.message,this._candidates=[]}finally{this._loading=!1}}_flatten(e){const t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entityId:e.entity_id,vendorName:i.name,blasterName:e.name,applianceLabel:i.appliance_label||"Appliance",applianceHelp:i.appliance_help||""});return t}get _selected(){return this._candidates.find(e=>e.entityId===this._entityId)}_autofillName(){if(this._nameEdited)return;const e=this._selected;if(!e)return;const t=this._appliance.trim();this._name=(t?`${e.blasterName}: ${t}`:e.blasterName).trim()}_onVendorChange(e){this._entityId=e.target.value,this._autofillName()}_onApplianceInput(e){this._appliance=e.target.value,this._autofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._selected;if(e)if(this._appliance.trim())if(this._name.trim()){this._busy=!0,this._error=null;try{const t=await this.api.createPluckedBlaster({vendor_entity_id:e.entityId,appliance:this._appliance.trim(),name:this._name.trim()});this.dispatchEvent(new CustomEvent("blaster-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("common.name_required");else this._error=ke("pluckdlg.appliance_required");else this._error=ke("pluckdlg.blaster_required")}render(){const e=this._selected;return B`
            <ha-dialog
                open
                heading=${ke("pluckdlg.add_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                ${this._loading?B`<div class="muted">${ke("pluckdlg.loading_blasters")}</div>`:0===this._candidates.length?B`<div class="muted">
                            ${ke("pluckdlg.no_blasters")}
                        </div>`:B`
                            <div class="field">
                                <label>${ke("pluckdlg.pluck_from")}</label>
                                <select
                                    .value=${this._entityId}
                                    @change=${this._onVendorChange}
                                >
                                    <option value="">${ke("pluckdlg.select_blaster")}</option>
                                    ${this._candidates.map(e=>B`<option
                                            value=${e.entityId}
                                        >
                                            ${e.vendorName}: ${e.blasterName}
                                        </option>`)}
                                </select>
                            </div>

                            <div class="field">
                                <label>${e?.applianceLabel??ke("pluckdlg.appliance")}</label>
                                <input
                                    type="text"
                                    .value=${this._appliance}
                                    placeholder=${ke("pluckdlg.appliance_placeholder")}
                                    required
                                    @input=${this._onApplianceInput}
                                />
                                ${e?.applianceHelp?B`<div class="help">
                                          ${e.applianceHelp}
                                      </div>`:""}
                            </div>

                            <div class="field">
                                <label>${ke("common.name")}</label>
                                <input
                                    type="text"
                                    .value=${this._name}
                                    placeholder=${ke("pluckdlg.name_placeholder")}
                                    @input=${e=>{this._name=e.target.value,this._nameEdited=!0}}
                                />
                            </div>
                        `}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${ke("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy||0===this._candidates.length}
                    >
                        ${this._busy?ke("common.creating"):ke("common.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};Aa.styles=[Bi,n`
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .muted {
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin: 12px 0;
        }
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #455a64;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],Aa.prototype,"api",void 0),e([pe()],Aa.prototype,"pendingEntity",void 0),e([ge()],Aa.prototype,"_candidates",void 0),e([ge()],Aa.prototype,"_entityId",void 0),e([ge()],Aa.prototype,"_appliance",void 0),e([ge()],Aa.prototype,"_name",void 0),e([ge()],Aa.prototype,"_busy",void 0),e([ge()],Aa.prototype,"_loading",void 0),e([ge()],Aa.prototype,"_error",void 0),Aa=e([ue("ir-pluck-add-remote-dialog")],Aa);let za=class extends se{constructor(){super(...arguments),this.integration="",this._commandName="",this._busy=!1,this._creating=!1,this._error=null,this._captures=null,this._aliases=[],this._validations=[]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _pluck(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.runPluck({integration:this.integration,vendor_entity_id:this.blaster.vendor_entity_id??"",appliance:this.blaster.appliance??"",command_name:e});t.error?this._error=t.message??ke("pluckdlg.pluck_failed"):t.signals&&t.signals.length>0?(this._captures=t.signals,this._aliases=t.signals.map(e=>e.suggested_alias),this._validations=await Promise.all(t.signals.map(e=>this.api.validatePronto(e.code??"").catch(()=>null)))):this._error=ke("pluckdlg.no_response")}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=ke("assign.command_required")}_removeCapture(e){this._captures&&(this._captures=this._captures.filter((t,i)=>i!==e),this._aliases=this._aliases.filter((t,i)=>i!==e),this._validations=this._validations.filter((t,i)=>i!==e),0===this._captures.length&&(this._captures=null))}async _create(){if(this._captures&&0!==this._captures.length){this._creating=!0,this._error=null;try{const e=[];for(let t=0;t<this._captures.length;t++){const i=this._captures[t],a=await this.api.createPluckedSignal({device_id:this.blaster.id,pronto:i.code??"",command_name:i.plucked_command_name,alias:this._aliases[t].trim()});e.push(a)}this.dispatchEvent(new CustomEvent("signals-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._creating=!1}}}_renderValid(e,t){const i=this._validations[t]??null,a=i?.recognized_protocol??e.decoded_protocol??null,r=null!=i?.frequency_khz?i.frequency_khz.toFixed(1):(e.frequency/1e3).toFixed(1),o=i?.burst_pair_count??null;return B`
            <div class="valid-box">
                <div class="valid-head">
                    <ha-svg-icon .path=${"M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"}></ha-svg-icon>
                    ${a?ke("pluckdlg.recognized_as",{protocol:a}):ke("pluckdlg.valid_pronto")}
                </div>
                <div class="valid-sub">
                    ${r} kHz${null!=o?` · ${o} burst pairs`:""}
                </div>
            </div>
        `}_renderError(){return this._error?B`
            <div class="pluck-error">
                <ha-svg-icon .path=${"M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z"}></ha-svg-icon>
                <span>${this._error}</span>
            </div>
        `:""}_renderCommandState(){return B`
            <div class="field">
                <label>${ke("assign.command_name")}</label>
                <input
                    type="text"
                    .value=${this._commandName}
                    placeholder=${ke("pluckdlg.command_placeholder")}
                    autofocus
                    @input=${e=>this._commandName=e.target.value}
                    @keydown=${e=>{"Enter"===e.key&&this._pluck()}}
                />
                <div class="help">
                    ${ke("pluckdlg.command_help")}
                </div>
            </div>
            ${this._renderError()}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${ke("common.cancel")}
                </button>
                <button
                    class="action-btn pluck-btn"
                    @click=${this._pluck}
                    ?disabled=${this._busy}
                >
                    ${this._busy?ke("pluckdlg.plucking"):ke("pluckdlg.pluck")}
                </button>
            </div>
        `}_renderCaptures(e){const t=e.length>1;return B`
            ${this._renderError()}
            <div class="captured-label">
                ${ke("pluckdlg.captured")} ${t?`(${e.length})`:""}
            </div>
            ${e.map((e,i)=>B`
                    <div class="capture">
                        ${t?B`<button
                                  class="remove-btn"
                                  title=${ke("pluckdlg.remove_capture")}
                                  @click=${()=>this._removeCapture(i)}
                              >
                                  &times;
                              </button>`:""}
                        <div class="pronto">${e.code}</div>
                        ${this._renderValid(e,i)}
                        <div class="field">
                            <label>${ke("pluckdlg.alias")}</label>
                            <input
                                type="text"
                                .value=${this._aliases[i]??""}
                                @input=${e=>{const t=e.target.value,a=[...this._aliases];a[i]=t,this._aliases=a}}
                            />
                        </div>
                    </div>
                `)}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._creating}
                >
                    ${ke("common.cancel")}
                </button>
                <button
                    class="action-btn create-btn"
                    @click=${this._create}
                    ?disabled=${this._creating}
                >
                    ${this._creating?ke("common.saving"):ke("common.create")}
                </button>
            </div>
        `}render(){return B`
            <ha-dialog
                open
                heading=${ke("pluckdlg.signal_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._captures?this._renderCaptures(this._captures):this._renderCommandState()}
            </ha-dialog>
        `}};za.styles=[Bi,n`
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus {
            outline: none;
            border-color: #455a64;
        }
        .pluck-error {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 12px 0;
            padding: 8px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border-left: 3px solid var(--warning-color, #ff9800);
            color: var(--primary-text-color);
            font-size: 0.85rem;
            line-height: 1.3;
        }
        .pluck-error ha-svg-icon {
            --mdc-icon-size: 18px;
            color: var(--warning-color, #ff9800);
            flex-shrink: 0;
        }
        .captured-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--secondary-text-color);
            margin: 12px 0 6px;
        }
        .capture {
            position: relative;
            margin-bottom: 12px;
        }
        .capture + .capture {
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
        }
        .remove-btn {
            position: absolute;
            top: 6px;
            right: 6px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            font-size: 1.1rem;
            line-height: 1;
            cursor: pointer;
            padding: 2px 6px;
        }
        .remove-btn:hover {
            color: var(--error-color, #c62828);
        }
        .pronto {
            font-family: var(--code-font-family, monospace);
            font-size: 0.72rem;
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px;
            max-height: 96px;
            overflow: auto;
            word-break: break-all;
        }
        .valid-box {
            margin-top: 8px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            padding: 8px 10px;
        }
        .valid-head {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            color: #2e7d32;
        }
        .valid-head ha-svg-icon {
            --mdc-icon-size: 16px;
        }
        .valid-sub {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .pluck-btn,
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .pluck-btn:hover:not(:disabled),
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],za.prototype,"api",void 0),e([pe({attribute:!1})],za.prototype,"blaster",void 0),e([pe()],za.prototype,"integration",void 0),e([ge()],za.prototype,"_commandName",void 0),e([ge()],za.prototype,"_busy",void 0),e([ge()],za.prototype,"_creating",void 0),e([ge()],za.prototype,"_error",void 0),e([ge()],za.prototype,"_captures",void 0),e([ge()],za.prototype,"_aliases",void 0),e([ge()],za.prototype,"_validations",void 0),za=e([ue("ir-pluck-signal-dialog")],za);const Da="M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z",Ea="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let Ia=class extends se{constructor(){super(...arguments),this.pendingEntity="",this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._vendorIntegration={},this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._promoteTarget=null,this._pluckDialog=null,this._editSignal=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),a=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||a&&t.includes(a)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(a,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:a}=t;if(void 0===i||void 0===a||i===a)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[n]=o.splice(i,1);o.splice(a,0,n),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("plucked",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i,a]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!1,min_hits:0,source:"plucked"}),this.api.listDevices(),this.api.listTriggers(),this.api.listPluckVendors().catch(()=>({vendors:[]}))]);this._devices=e,this._hairDevices=t,this._triggers=i,this._vendorIntegration=this._mapIntegrations(a.vendors),this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_mapIntegrations(e){const t={};for(const i of e)for(const e of i.blasters)t[e.entity_id]=i.integration;return t}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onBlasterCreated(e){this._createRemoteOpen=!1,this.pendingEntity="",await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openPluckSignal(e,t){t.stopPropagation();const i=e.vendor_entity_id?this._vendorIntegration[e.vendor_entity_id]??"":"";i?this._pluckDialog={device:e,integration:i}:this._error=ke("pluck.vendor_unavailable")}async _onSignalsCreated(){this._pluckDialog=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this blaster",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deletePluckedBlaster(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("plucked"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),a=this._devices.findIndex(t=>t.id===e);if(a>=0){const e=[...this._devices];e[a]={...e[a],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,a){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=a?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,a=i.length;this._testResult=e===a?1===a?ke("mirror.sent"):ke("mirror.sent_all_n",{sent:e,total:a}):0===e?ke("mirror.failed"):`Sent (${e}/${a})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_a(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_a(t,e)).length}_openTriggerDialog(e,t,i){const a=this._triggers.filter(e=>_a(e,t));if(0===a.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}render(){const e=this._devices.length;return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${Da}></ha-svg-icon>
                    ${ke("pluck.title")}
                    ${this._loading?"":B`<span class="count"
                              >(${e} ${1===e?"blaster":"blasters"})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        ${ke("pluck.add_blaster")}
                    </button>
                </div>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">${ke("common.loading_plain")}</div>`:0===e?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${Da}></ha-svg-icon>
                            <h3>${ke("pluck.empty_title")}</h3>
                            <p>${ke("pluck.empty_body")}</p>
                            <p class="hint">${ke("pluck.empty_hint")}</p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${He(this._remotesVersion,Me(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?B`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title=${ke("pluck.clear_all_title")}
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              Clear All
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return B`
            <ha-card class="device pluck-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${Ea}
                                          title=${ke("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title=${ke("cmdrow.rename")}
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??ke("pluck.blaster_fallback")}</span
                                      >`}
                            ${e.appliance?B`<span
                                      class="appliance-badge"
                                      @click=${e=>e.stopPropagation()}
                                      >${e.appliance}</span
                                  >`:""}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${1===e.signal_count?"signal":"signals"}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                      >${ke("sniffer.hair_device")}</span
                                  >`:e.label?B`<span
                                        class="status-badge promote-badge"
                                        title=${ke("pluck.promote_title")}
                                        @click=${t=>this._promoteDevice(e,t)}
                                        >${ke("sniffer.promote")}</span
                                    >`:""}
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>${ke("sniffer.signals_head",{count:e.signals.length})}</span>
                    <button
                        class="create-signal-btn"
                        title=${ke("pluck.pluck_signal_title")}
                        @click=${t=>this._openPluckSignal(e,t)}
                    >
                        ${ke("pluck.pluck_signal")}
                    </button>
                </div>
                ${0===e.signals.length?B`<div class="no-signals-row">
                          <span class="no-signals"
                              >${ke("pluck.no_signals")}</span
                          >
                      </div>`:B`
                          <div class="signal-list">
                              ${He(this._signalsVersion,Me(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title=${ke("pluck.delete_blaster_title")}
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >
                        ${ke("pluck.delete_blaster")}
                    </button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const a=this._testingSignalId===t.id;return B`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${Ea}
                    title=${ke("devdetail.drag")}
                ></ha-svg-icon>
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${e}
                        .signal=${t}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${e=>this._error=e.detail}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${a&&this._testResult?B`<span class="test-result">${this._testResult}</span>`:B`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?B`<button
                          title=${ke("cmdrow.edit_code")}
                          @click=${i=>this._openEditSignal(e,t,i)}
                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                      >
                          <ha-svg-icon
                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                              style="--mdc-icon-size:10px"
                          ></ha-svg-icon>
                      </button>`:""}
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:ke("mirror.assign_title")}
                        @click=${a=>{a.stopPropagation(),this._onAssignClick(e,t,i,a)}}
                    >
                        ${ke("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${a}
                        title=${ke("clips.test_title")}
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >
                        ${a?this._testResult??ke("mirror.sending"):ke("mirror.test")}
                    </button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?ke("mirror.trigger_edit"):ke("sniffer.trigger_create")}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >
                        ${ke("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >
                        ${ke("common.delete")}
                    </button>
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._createRemoteOpen?B`<ir-pluck-add-remote-dialog
                      .api=${this.api}
                      .pendingEntity=${this.pendingEntity}
                      @blaster-created=${this._onBlasterCreated}
                      @closed=${()=>{this._createRemoteOpen=!1,this.pendingEntity=""}}
                  ></ir-pluck-add-remote-dialog>`:""}

            ${this._promoteTarget?B`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._pluckDialog?B`<ir-pluck-signal-dialog
                      .api=${this.api}
                      .blaster=${this._pluckDialog.device}
                      .integration=${this._pluckDialog.integration}
                      @signals-created=${this._onSignalsCreated}
                      @closed=${()=>this._pluckDialog=null}
                  ></ir-pluck-signal-dialog>`:""}

            ${this._editSignal?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .hasTrigger=${this._hasTrigger(this._editSignal.signal)}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._assignSignal?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._deleteSignal?B`<ir-confirm-dialog
                      title=${ke("sniffer.del_signal_title")}
                      message=${ke("sniffer.del_signal_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?B`<ir-confirm-dialog
                      title=${ke("pluck.clear_all_confirm_title")}
                      message=${ke("pluck.clear_all_confirm_msg")}
                      confirmLabel="Clear All"
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?B`<ir-confirm-dialog
                      title=${ke("pluck.del_blaster_confirm_title")}
                      message=${this._deleteRemoteCount>0?$e("clips.del_remote_msg_n",this._deleteRemoteCount,{name:this._deleteRemoteLabel??""}):ke("clips.del_remote_msg",{name:this._deleteRemoteLabel??""})}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_a(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .byteHash=${this._triggerDialog.signal.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                      .alias=${this._triggerDialog.signal.alias||null}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}

            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title=${ke("mirror.del_trigger_title")}
                      message=${ke("devdetail.del_trigger_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};function Ta(e){if(!e)return"";try{const t=Date.now()-new Date(e).getTime();return t<6e4?ke("rel.just_now"):t<36e5?`${Math.floor(t/6e4)}m`:t<864e5?`${Math.floor(t/36e5)}h`:`${Math.floor(t/864e5)}d`}catch{return""}}Ia.styles=[Li,n`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: #455a64;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        /* Toolbar "+ Add Blaster": shared chip anatomy, slate accent. */
        .action-btn.create-btn {
            color: #78909c;
            border-color: #78909c;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(120, 144, 156, 0.12);
        }
        /* Card-internal "+ Pluck Signal": borderless slate text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Blaster accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 10px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #78909c;
            cursor: pointer;
        }
        .create-signal-btn:hover:not(:disabled) {
            background: none;
            text-decoration: underline;
        }
        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #455a64;
            opacity: 0.5;
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }
        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .device.pluck-device {
            border: 1px solid rgba(69, 90, 100, 0.3);
            overflow: hidden;
        }
        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #455a64;
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:hover {
            border-bottom-color: #455a64;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #455a64;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .appliance-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            letter-spacing: 0.02em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(69, 90, 100, 0.15);
            color: #455a64;
            border: 1px solid rgba(69, 90, 100, 0.35);
        }
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .stat {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }
        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        .signal-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .no-signals-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .remote-footer {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
            padding-right: 8px;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .test-result {
            color: #2e7d32;
            font-weight: 500;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
    `],e([pe({attribute:!1})],Ia.prototype,"api",void 0),e([pe({attribute:!1})],Ia.prototype,"hass",void 0),e([pe()],Ia.prototype,"pendingEntity",void 0),e([ge()],Ia.prototype,"_devices",void 0),e([ge()],Ia.prototype,"_hairDevices",void 0),e([ge()],Ia.prototype,"_triggers",void 0),e([ge()],Ia.prototype,"_loading",void 0),e([ge()],Ia.prototype,"_error",void 0),e([ge()],Ia.prototype,"_expandedId",void 0),e([ge()],Ia.prototype,"_expandedDevice",void 0),e([ge()],Ia.prototype,"_confirmClearAll",void 0),e([ge()],Ia.prototype,"_deleteRemoteId",void 0),e([ge()],Ia.prototype,"_deleteRemoteLabel",void 0),e([ge()],Ia.prototype,"_deleteRemoteCount",void 0),e([ge()],Ia.prototype,"_editingDeviceId",void 0),e([ge()],Ia.prototype,"_editLabel",void 0),e([ge()],Ia.prototype,"_createRemoteOpen",void 0),e([ge()],Ia.prototype,"_promoteTarget",void 0),e([ge()],Ia.prototype,"_pluckDialog",void 0),e([ge()],Ia.prototype,"_editSignal",void 0),e([ge()],Ia.prototype,"_assignSignal",void 0),e([ge()],Ia.prototype,"_deleteSignal",void 0),e([ge()],Ia.prototype,"_triggerDialog",void 0),e([ge()],Ia.prototype,"_triggerEditDialog",void 0),e([ge()],Ia.prototype,"_triggerPopover",void 0),e([ge()],Ia.prototype,"_assignedPopover",void 0),e([ge()],Ia.prototype,"_receivers",void 0),e([ge()],Ia.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],Ia.prototype,"_testDialog",void 0),e([ge()],Ia.prototype,"_testEmitters",void 0),e([ge()],Ia.prototype,"_testingSignalId",void 0),e([ge()],Ia.prototype,"_testResult",void 0),e([ge()],Ia.prototype,"_remotesVersion",void 0),e([ge()],Ia.prototype,"_signalsVersion",void 0),Ia=e([ue("ir-pluck")],Ia);const Ra="M 19.39,4.60 C 16.51,1.71 11.78,1.71 8.89,4.60 C 6.00,7.49 6.00,12.21 8.89,15.10 C 11.78,17.99 16.51,17.99 19.39,15.10 C 22.28,12.21 22.28,7.49 19.39,4.60 M 9.29,14.70 C 6.63,12.03 6.63,7.67 9.29,5.00 C 11.96,2.34 16.32,2.34 18.99,5.00 C 21.66,7.67 21.66,12.03 18.99,14.70 C 16.32,17.36 11.96,17.36 9.29,14.70 M 4.85,19.14 C 4.29,18.58 3.40,18.58 2.83,19.14 C 2.27,19.71 2.27,20.60 2.83,21.16 C 3.40,21.73 4.29,21.73 4.85,21.16 C 5.42,20.60 5.42,19.71 4.85,19.14 M 3.24,20.76 C 2.89,20.41 2.89,19.89 3.24,19.55 C 3.58,19.20 4.10,19.20 4.45,19.55 C 4.79,19.89 4.79,20.41 4.45,20.76 C 4.10,21.10 3.58,21.10 3.24,20.76 M 22.99,9.57 C 22.91,7.10 21.84,4.82 19.98,3.20 C 16.65,0.28 11.62,0.26 8.31,3.20 C 5.52,5.67 4.57,9.49 5.86,12.96 C 6.33,14.19 6.02,15.55 5.13,16.43 C 4.65,16.92 4.04,17.24 3.40,17.32 C 2.79,17.40 2.25,17.71 1.82,18.13 C 0.75,19.20 0.73,21.00 1.78,22.09 C 1.80,22.11 1.82,22.13 1.84,22.15 C 2.37,22.68 3.07,22.98 3.82,23.00 C 4.61,23.02 5.32,22.72 5.88,22.15 C 6.31,21.73 6.57,21.18 6.67,20.60 C 6.77,19.93 7.07,19.34 7.56,18.86 C 8.45,17.97 9.82,17.69 11.03,18.13 C 14.28,19.36 17.96,18.56 20.40,16.11 C 22.12,14.39 23.07,11.99 22.99,9.57 M 11.23,17.61 C 9.82,17.08 8.20,17.40 7.15,18.45 C 6.59,19.02 6.22,19.75 6.10,20.51 C 6.02,21.00 5.80,21.42 5.46,21.77 C 5.01,22.21 4.43,22.43 3.82,22.43 C 3.17,22.43 2.61,22.19 2.18,21.73 C 1.34,20.84 1.38,19.42 2.21,18.56 C 2.55,18.21 2.99,17.97 3.48,17.89 C 4.25,17.77 4.97,17.40 5.54,16.84 C 6.59,15.79 6.93,14.19 6.39,12.76 C 5.17,9.53 6.06,5.93 8.69,3.63 C 11.80,0.88 16.49,0.88 19.60,3.63 C 19.74,3.73 19.88,3.87 20.00,3.99 C 21.49,5.49 22.36,7.45 22.42,9.57 C 22.48,11.89 21.64,14.07 20.00,15.71 C 17.70,18.01 14.26,18.74 11.23,17.61 M 17.58,10.86 L 10.71,10.86 C 10.55,10.86 10.43,10.98 10.43,11.14 C 10.43,11.22 10.47,11.30 10.51,11.34 C 10.55,11.38 10.63,11.43 10.71,11.43 L 17.58,11.43 C 17.74,11.43 17.86,11.30 17.86,11.14 C 17.86,10.98 17.72,10.88 17.58,10.86 M 17.88,8.54 C 17.88,8.38 17.76,8.25 17.60,8.25 L 10.73,8.25 C 10.57,8.25 10.45,8.38 10.45,8.54 C 10.45,8.62 10.49,8.70 10.53,8.74 C 10.57,8.78 10.65,8.82 10.73,8.82 L 17.60,8.82 C 17.72,8.82 17.86,8.68 17.88,8.54";let Pa=class extends se{constructor(){super(...arguments),this._device=null,this._loading=!0,this._error=null,this._triggers=[],this._receivers=[],this._hasReceivers=!0,this._filter="all",this._search="",this._bloomIds=new Set,this._assignSignal=null,this._assignedPopover=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._confirmDeleteTriggerId=null,this._deleteSignal=null,this._editSignal=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._unsubSignals=null,this._unsubUpdated=null,this._refreshTimer=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),a=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||a&&t.includes(a)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe(),this._removePopoverDismiss(),null!==this._refreshTimer&&(clearTimeout(this._refreshTimer),this._refreshTimer=null)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({source:"echo",min_hits:0}),this.api.listTriggers(),this.api.getSnifferStatus()]);this._triggers=t,this._hasReceivers=i.has_receivers;const a=e.find(e=>e.fingerprint===ha);this._device=a?await this.api.getUnknownDevice(a.id):null,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}async _refreshDevice(){if(this._device)try{this._device=await this.api.getUnknownDevice(this._device.id)}catch{await this._load()}else await this._load()}async _subscribe(){try{this._unsubSignals=await this.api.subscribeUnknownSignals(e=>this._onLiveSignal(e))}catch{}try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshDots()})}catch{}}async _unsubscribe(){this._unsubSignals&&(await this._unsubSignals(),this._unsubSignals=null),this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshDots(){try{this._triggers=await this.api.listTriggers()}catch{}await this._refreshDevice()}_onLiveSignal(e){e.device_fingerprint===ha&&(this._bloomIds=new Set([...this._bloomIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._bloomIds);t.delete(e.signal_id),this._bloomIds=t},2500),null!==this._refreshTimer&&clearTimeout(this._refreshTimer),this._refreshTimer=window.setTimeout(()=>{this._refreshTimer=null,this._refreshDevice()},300))}_friendlyReceiver(e){const t=this._receivers.find(t=>t.entity_id===e);if(t?.name)return t.name;const i=this.hass?.states?.[e];return i?.attributes?.friendly_name??e}_receiverArea(e){const t=this.hass?.entities?.[e],i=t?.area_id??(t?.device_id?this.hass?.devices?.[t.device_id]?.area_id:null);return i?this.hass?.areas?.[i]?.name??null:null}_decodedDisplay(e){const t=e.decoded_fingerprint;if(!t)return null;const i=t.split(":");return i.length>=3?`${i[0]} ${i[1]} : ${i.slice(2).join(":")}`:t}_rowView(e){const t=e.echo_source??"",i=t.indexOf(" -- via "),a=i>=0?t.slice(0,i):t,r=i>=0?t.slice(i+8):"",o=r?r.split(", "):[];let n,s=null;const l=["Manual test send","Catalog test"].find(e=>a.startsWith(e));"automation send"===a?n=ke("mirror.chip_automation"):"integration send"===a?n=ke("mirror.chip_integration"):l?(n=ke("mirror.chip_test"),s=a.slice(l.length).replace(/^:\s*/,"").trim()||null):a?(n=ke("mirror.chip_device"),s=a):n=ke("mirror.chip_send");const d=(e.fingerprint??"").startsWith("mirror-unknown::"),c=(d&&"Unknown send"===e.alias?"":e.alias)||s||this._decodedDisplay(e)||(e.sl_pattern?[...e.sl_pattern].map(e=>"L"===e?"◆":"◇").join(""):null)||ke("mirror.unknown_title"),p=e.decoded_protocol??e.protocol,g=!e.decoded_protocol,m=o.length>2?ke("mirror.via_n",{count:o.length}):r?ke("mirror.via",{name:r}):"";let u=null,h=!1;if(this._hasReceivers){const t=e.heard_by??[];if(0===t.length)u=ke("mirror.not_heard");else{h=!0;const e=t.map(e=>this._receiverArea(e));if(e.every(e=>null!==e))u=ke("mirror.heard_in",{areas:[...new Set(e)].join(", ")});else{const e=t.map(e=>this._friendlyReceiver(e));u=ke("mirror.heard_by",{names:e.join(", ")})}}}return{sig:e,title:c,pill:p??null,pillRaw:g,via:m,viaFull:r,emitters:o,chip:n,heard:u,heardOk:h,unknownSend:d}}_rows(){const e=[...this._device?.signals??[]].sort((e,t)=>(t.last_seen??"").localeCompare(e.last_seen??""));return e.map(e=>this._rowView(e))}_filteredRows(e){let t=e;"notheard"===this._filter?t=t.filter(e=>0===(e.sig.heard_by??[]).length):"all"!==this._filter&&(t=t.filter(e=>e.emitters.includes(this._filter)));const i=this._search.trim().toLowerCase();return i&&(t=t.filter(e=>[e.title,e.pill??"",e.viaFull,e.chip,e.sig.decoded_fingerprint??"",e.sig.alias??""].join(" ").toLowerCase().includes(i))),t}_triggerCountFor(e){return this._triggers.filter(t=>_a(t,e)).length}_onAssignClick(e,t){if(!this._device)return;if(!e.assigned_to?.length)return void(this._assignSignal={signal:e,initialMode:"existing"});const i=t?.currentTarget,a=i?.getBoundingClientRect();this._assignedPopover={signal:e,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&(this._assignSignal={signal:e.signal,initialMode:"existing"})}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._refreshDots()}_openTriggerDialog(e,t){const i=this._triggers.filter(t=>_a(t,e));if(0===i.length)return void(this._triggerDialog=e);const a=t?.currentTarget,r=a?.getBoundingClientRect();this._triggerPopover={signal:e,top:r?r.bottom+4:120,left:r?Math.max(8,r.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog=e.signal)}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._closeTriggerDialog(),this._confirmDeleteTriggerId=e}async _confirmDeleteTrigger(){const e=this._confirmDeleteTriggerId;if(this._confirmDeleteTriggerId=null,e)try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch(e){this._error=ke("common.delete_failed",{message:e.message})}}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _sendTest(e){if(!this._testDialog)return;const t=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,a=i.length;this._testResult=e===a?1===a?ke("mirror.sent"):ke("mirror.sent_all_n",{sent:e,total:a}):0===e?ke("mirror.failed"):ke("mirror.sent_partial",{sent:e,total:a})}catch{this._testResult=ke("mirror.error")}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}async _onSignalEdited(){this._editSignal=null,await this._refreshDevice()}async _confirmDeleteSignal(){const e=this._deleteSignal;if(this._deleteSignal=null,e&&this._device)try{await this.api.deleteSignal(this._device.id,e.id),await this._refreshDevice()}catch(e){this._error=ke("common.delete_failed",{message:e.message})}}render(){const e=this._rows(),t=this._filteredRows(e);return B`
            <div class="tab-head">
                <span class="title">
                    <ha-svg-icon .path=${Ra}></ha-svg-icon>
                    HAIR Mirror
                    ${this._loading?"":B`<span class="count"
                              >(${$e("mirror.signals",e.length)})</span
                          >`}
                </span>
            </div>
            ${this._error?B`<div class="error">${this._error}</div>`:""}
            ${this._loading&&!this._device?B`<div class="loading">${ke("panel.loading")}</div>`:0===e.length?this._renderEmpty():B`
                        ${this._renderStats(e)}
                        ${this._renderToolbar(e)}
                        <div class="rows">
                            ${0===t.length?B`<div class="no-match">
                                      ${ke("mirror.no_match")}
                                  </div>`:t.map(e=>this._renderRow(e))}
                        </div>
                    `}
            ${this._renderDialogs()}
        `}_renderStats(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Set;for(const t of e)t.emitters.forEach(e=>i.add(e));const a=this._device?.last_seen;return B`
            <div class="stats">
                <div class="stat">
                    <div class="v">${this._device?.hit_count??0}</div>
                    <div class="l">${ke("mirror.stat_sends")}</div>
                </div>
                ${this._hasReceivers?B`
                          <div class="stat">
                              <div class="v ${t?"warn":""}">
                                  ${t}
                              </div>
                              <div class="l">${ke("mirror.stat_not_heard")}</div>
                          </div>
                      `:""}
                <div class="stat">
                    <div class="v">${i.size}</div>
                    <div class="l">${ke("mirror.stat_emitters")}</div>
                </div>
                <div class="stat">
                    <div class="v">${e.length}</div>
                    <div class="l">${ke("mirror.stat_signals")}</div>
                </div>
                <span class="updated">
                    ${this._hasReceivers?a?Ta(a)===ke("rel.just_now")?ke("mirror.last_send_just"):ke("mirror.last_send_ago",{rel:Ta(a)}):"":ke("mirror.no_receivers")}
                </span>
            </div>
        `}_renderToolbar(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Map;for(const t of e)for(const e of t.emitters)i.set(e,(i.get(e)??0)+1);return B`
            <div class="toolbar">
                <button
                    class="fchip ${"all"===this._filter?"on":""}"
                    @click=${()=>this._filter="all"}
                >
                    ${ke("mirror.filter_all",{count:e.length})}
                </button>
                ${this._hasReceivers?B`
                          <button
                              class="fchip warnc ${"notheard"===this._filter?"on":""}"
                              @click=${()=>this._filter="notheard"}
                          >
                              ${ke("mirror.filter_not_heard",{count:t})}
                          </button>
                      `:""}
                ${[...i.entries()].map(([e,t])=>B`
                        <button
                            class="fchip ${this._filter===e?"on":""}"
                            @click=${()=>this._filter=e}
                        >
                            ${e} (${t})
                        </button>
                    `)}
                <input
                    class="search"
                    type="text"
                    placeholder=${ke("mirror.search")}
                    .value=${this._search}
                    @input=${e=>{this._search=e.target.value}}
                />
            </div>
        `}_renderRow(e){const t=e.sig,i=this._bloomIds.has(t.id),a=!!t.code,r=this._testingSignalId===t.id;return B`
            <div class="mrow ${i?"bloom":""}">
                <div class="mrow-main">
                    <div class="mrow-title">
                        <span class="name">${e.title}</span>
                        ${e.pill?B`<span
                                  class="pill ${e.pillRaw?"raw":""}"
                                  >${e.pill}</span
                              >`:""}
                        ${(t.send_count??1)>1?B`<span
                                  class="repeat-indicator"
                                  title=${ke("mirror.sends_times",{count:t.send_count})}
                                  ><ha-svg-icon
                                      .path=${"M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"}
                                  ></ha-svg-icon
                                  >${t.send_count}</span
                              >`:""}
                        ${(t.repeat_count??1)>1&&t.decoded_protocol?B`<span
                                  class="ditto-indicator"
                                  title=${ke("cmdrow.dittos",{count:t.repeat_count})}
                                  ><ha-svg-icon
                                      .path=${"M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z"}
                                  ></ha-svg-icon
                                  >${t.repeat_count}</span
                              >`:""}
                    </div>
                    ${e.unknownSend?B`
                              <div class="mrow-hint">
                                  ${ke("mirror.unknown_hint").split("{name}")[0]}<em
                                      class="hint-emitter"
                                      >${e.emitters[0]??ke("mirror.the_blaster")}</em
                                  >${ke("mirror.unknown_hint").split("{name}")[1]??""}
                              </div>
                          `:B`
                              <div class="mrow-sub">
                                  ${e.via?B`<span title=${e.viaFull}
                                            >${e.via}</span
                                        >`:""}
                                  ${null!==e.heard?B`
                                            <span class="arrow"
                                                >&#10142;</span
                                            >
                                            <span
                                                class=${e.heardOk?"heard":"not-heard"}
                                                >${e.heard}</span
                                            >
                                        `:""}
                                  <span class="src-chip">${e.chip}</span>
                              </div>
                          `}
                </div>
                <div class="mrow-meta">
                    <span class="counts"
                        >${t.hit_count}
                        ${1===t.hit_count?"send":"sends"}${t.last_seen?B` &middot; ${Ta(t.last_seen)}`:""}</span
                    >
                    ${t.code?B`
                              <button
                                  class="code-btn"
                                  title=${ke("cmdrow.edit_code")}
                                  @click=${e=>{e.stopPropagation(),this._editSignal=t}}
                              >
                                  <ha-svg-icon
                                      .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                      style="--mdc-icon-size:10px"
                                  ></ha-svg-icon>
                              </button>
                          `:""}
                    <button
                        class="action-btn assign-btn"
                        ?disabled=${!a}
                        title=${a?t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?ke("mirror.assigned_one",{device:t.assigned_to[0].device_name,command:t.assigned_to[0].command_name}):ke("mirror.assigned_n",{count:t.assignment_count})+`\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:ke("mirror.assign_title"):ke("mirror.assign_disabled")}
                        @click=${e=>{e.stopPropagation(),this._onAssignClick(t,e)}}
                    >${ke("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${!a||r}
                        title=${ke(a?"mirror.test_title":"mirror.test_disabled")}
                        @click=${e=>{e.stopPropagation(),this._testDialog=t}}
                    >${r?this._testResult??ke("mirror.sending"):ke("mirror.test")}</button>
                    <button
                        class="action-btn trigger-btn"
                        ?disabled=${!a}
                        title=${a?this._triggerCountFor(t)>0?ke("mirror.trigger_edit"):ke("mirror.trigger_create"):ke("mirror.trigger_disabled")}
                        @click=${e=>{e.stopPropagation(),this._openTriggerDialog(t,e)}}
                    >${ke("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn delete-btn"
                        title=${ke("mirror.delete_title")}
                        @click=${e=>{e.stopPropagation(),this._deleteSignal=t}}
                    >${ke("common.delete")}</button>
                </div>
            </div>
        `}_renderEmpty(){return B`
            <div class="empty">
                <ha-svg-icon
                    class="empty-icon"
                    .path=${Ra}
                ></ha-svg-icon>
                <div class="empty-title">${ke("mirror.empty_title")}</div>
                <div class="empty-sub">
                    ${ke("mirror.empty_sub")}
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_a(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}
            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}
            ${this._triggerDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.fingerprint}
                      .byteHash=${this._triggerDialog.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.protocol}
                      .code=${this._triggerDialog.code}
                      .slPattern=${this._triggerDialog.sl_pattern??null}
                      .alias=${this._triggerDialog.alias||null}
                      .mirrorContext=${!0}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}
            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      .mirrorContext=${!0}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}
            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title=${ke("mirror.del_trigger_title")}
                      message=${ke("mirror.del_trigger_msg")}
                      confirmLabel=${ke("common.delete")}
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}
            ${this._deleteSignal?B`<ir-confirm-dialog
                      title=${ke("mirror.clear_title")}
                      message=${ke("mirror.clear_msg")}
                      confirmLabel=${ke("common.delete")}
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteSignal}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}
            ${this._assignSignal&&this._device?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._device.id}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${""}
                      .initialMode=${this._assignSignal.initialMode}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}
            ${this._editSignal&&this._device?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._device.id}
                      .signalId=${this._editSignal.id}
                      .initialPronto=${this._editSignal.code??""}
                      .initialAlias=${this._editSignal.alias??""}
                      .initialSendCount=${this._editSignal.send_count??1}
                      .initialDitto=${this._editSignal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.observed_repeat_count??0}
                      .hasTrigger=${this._triggerCountFor(this._editSignal)>0}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}
            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};Pa.styles=[Li,n`
            :host {
                display: block;
            }
            .loading,
            .no-match {
                text-align: center;
                color: var(--secondary-text-color);
                padding: 24px;
            }

            /* Tab header, same anatomy as the Sniffer/Clipper/Plucker
               titles; the mirror icon wears the tab's silver. */
            .tab-head {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
            }
            .title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 1.1rem;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .title ha-svg-icon {
                --mdc-icon-size: 24px;
                color: #607d8b;
            }
            .title .count {
                font-size: 0.85rem;
                font-weight: 400;
                color: var(--secondary-text-color);
            }
            .error {
                color: var(--error-color, #db4437);
                padding: 8px 0;
            }

            /* Stats strip: the silver sheen lives here, as texture.
               Deliberately slim (owner bench note: less air above and
               below) -- values and labels sit on one line per stat. */
            .stats {
                display: flex;
                align-items: baseline;
                gap: 22px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 14px;
                margin-bottom: 12px;
                background-image: linear-gradient(
                    105deg,
                    transparent 42%,
                    rgba(144, 164, 174, 0.12) 50%,
                    transparent 58%
                );
            }
            .stat {
                display: flex;
                align-items: baseline;
                gap: 5px;
            }
            .stat .v {
                font-size: 15px;
                font-weight: 600;
                color: var(--primary-text-color);
            }
            .stat .l {
                font-size: 10.5px;
                color: var(--secondary-text-color);
                letter-spacing: 0.4px;
            }
            .stat .v.warn {
                color: #e65100;
            }
            .stats .updated {
                margin-left: auto;
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }

            /* Toolbar */
            .toolbar {
                display: flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 14px;
                flex-wrap: wrap;
            }
            .fchip {
                font-size: 12.5px;
                padding: 5px 13px;
                border-radius: 16px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--secondary-text-color);
                font-family: inherit;
                cursor: pointer;
            }
            .fchip.on {
                background: #607d8b;
                border-color: #607d8b;
                color: #fff;
            }
            .fchip.warnc:not(.on) {
                color: #e65100;
                border-color: #ffcf9e;
            }
            .search {
                flex: 1 1 180px;
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: inherit;
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            .search:focus {
                outline: none;
                border-color: #607d8b;
            }

            /* Rows: each send is its own rounded card (owner bench note),
               matching the card language of the Devices, Sniffer, and
               Clipper surfaces instead of a welded table. */
            .rows {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .mrow {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 16px;
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                background: var(--card-background-color);
                /* Carries the soft exit after the bloom class drops --
                   same durations as the trigger card. */
                transition: box-shadow 300ms ease, border-color 300ms ease,
                            background 400ms ease;
            }
            .mrow:hover {
                background: var(--secondary-background-color);
            }
            /* The silver bloom a send makes while you watch: the WHOLE
               card glows and fades (owner bench note -- the old left-edge
               chip read as a sliver). Lifecycle is the trigger card's,
               verbatim, in silver: the animation fades to nothing over
               2.4s, the class's static styles snap back for one last
               pass (class held to 2500ms, see BLOOM_MS), then the class
               drops and the row's transitions carry the soft exit. */
            .mrow.bloom {
                border-color: #90a4ae;
                background: rgba(144, 164, 174, 0.08);
                animation: mirror-bloom 2.4s ease-out;
            }
            @keyframes mirror-bloom {
                0% {
                    background: rgba(144, 164, 174, 0.18);
                    border-color: #b0bec5;
                    box-shadow: 0 0 16px 4px rgba(144, 164, 174, 0.4);
                }
                30% {
                    background: rgba(144, 164, 174, 0.1);
                    border-color: #90a4ae;
                    box-shadow: 0 0 8px 2px rgba(144, 164, 174, 0.2);
                }
                60% {
                    background: rgba(144, 164, 174, 0.06);
                    box-shadow: 0 0 4px 1px rgba(144, 164, 174, 0.1);
                }
                100% {
                    background: transparent;
                    border-color: var(--divider-color);
                    box-shadow: none;
                }
            }
            .mrow-main {
                min-width: 0;
            }
            .mrow-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
            }
            .mrow-title .name {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .pill {
                font-size: 10px;
                letter-spacing: 0.4px;
                font-weight: 500;
                padding: 2px 7px;
                border-radius: 9px;
                background: rgba(33, 150, 243, 0.12);
                color: #1565c0;
                white-space: nowrap;
            }
            .pill.raw {
                background: rgba(230, 140, 60, 0.12);
                color: #b87333;
            }
            /* TX-knob indicators, same anatomy as the command rows'. */
            .repeat-indicator,
            .ditto-indicator {
                display: inline-flex;
                align-items: center;
                gap: 1px;
                font-size: 9px;
                font-weight: 600;
                opacity: 0.85;
            }
            .repeat-indicator {
                color: var(--warning-color, #ff9800);
            }
            .ditto-indicator {
                color: var(--primary-color);
            }
            .repeat-indicator ha-svg-icon,
            .ditto-indicator ha-svg-icon {
                --mdc-icon-size: 10px;
            }
            .mrow-sub {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
            }
            /* Unknown-send explanation: replaces the whole sub-line on
               foreign never-heard rows (owner wording). Plain prose, so
               it wraps like a sentence rather than flexing like chips. */
            .mrow-hint {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                line-height: 1.45;
                max-width: 46em;
            }
            /* The emitter's name reads as part of the sentence without
               a marker (owner bench note); italic says "this is YOUR
               device's name, not our words." */
            .mrow-hint .hint-emitter {
                font-style: italic;
            }
            .arrow {
                color: #b0bec5;
            }
            .heard {
                color: #2e7d32;
            }
            /* Neutral grey, not amber: one-way homes are normal. */
            .not-heard {
                color: #90a4ae;
            }
            .src-chip {
                font-size: 10.5px;
                padding: 1px 8px;
                border-radius: 8px;
                background: rgba(96, 125, 139, 0.12);
                color: #546e7a;
                white-space: nowrap;
            }
            .mrow-meta {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 10px;
                white-space: nowrap;
            }
            .counts {
                font-size: 12px;
                color: var(--secondary-text-color);
            }
            .code-btn {
                background: none;
                border: none;
                cursor: pointer;
                color: var(--secondary-text-color);
                padding: 2px;
                display: inline-flex;
                align-items: center;
            }

            /* Empty state: the feature explaining itself. */
            .empty {
                text-align: center;
                padding: 44px 20px 52px;
            }
            .empty-icon {
                --mdc-icon-size: 44px;
                color: #607d8b;
                margin-bottom: 12px;
            }
            .empty-title {
                font-size: 15px;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .empty-sub {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                margin-top: 6px;
                max-width: 420px;
                margin-left: auto;
                margin-right: auto;
                line-height: 1.5;
            }
        `],e([pe({attribute:!1})],Pa.prototype,"api",void 0),e([pe({attribute:!1})],Pa.prototype,"hass",void 0),e([ge()],Pa.prototype,"_device",void 0),e([ge()],Pa.prototype,"_loading",void 0),e([ge()],Pa.prototype,"_error",void 0),e([ge()],Pa.prototype,"_triggers",void 0),e([ge()],Pa.prototype,"_receivers",void 0),e([ge()],Pa.prototype,"_hasReceivers",void 0),e([ge()],Pa.prototype,"_filter",void 0),e([ge()],Pa.prototype,"_search",void 0),e([ge()],Pa.prototype,"_bloomIds",void 0),e([ge()],Pa.prototype,"_assignSignal",void 0),e([ge()],Pa.prototype,"_assignedPopover",void 0),e([ge()],Pa.prototype,"_triggerDialog",void 0),e([ge()],Pa.prototype,"_triggerEditDialog",void 0),e([ge()],Pa.prototype,"_triggerPopover",void 0),e([ge()],Pa.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],Pa.prototype,"_deleteSignal",void 0),e([ge()],Pa.prototype,"_editSignal",void 0),e([ge()],Pa.prototype,"_testDialog",void 0),e([ge()],Pa.prototype,"_testEmitters",void 0),e([ge()],Pa.prototype,"_testingSignalId",void 0),e([ge()],Pa.prototype,"_testResult",void 0),Pa=e([ue("ir-mirror")],Pa);let Ha=class extends se{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._expandedDeviceId=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._pluckersAvailable=!1,this._pendingPluckEntity="",this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&(function(e){const t=e||"en";if(t!==fe){fe=t;try{ye=new Intl.PluralRules(t)}catch{ye=new Intl.PluralRules("en")}}const i=t.toLowerCase();let a="en";if(ve[i])a=i;else{const e=i.split("-")[0];ve[e]&&(a=e)}be=a}(this.hass.language),this._api||this._init())}_init(){this._api=new he(this.hass),this._refreshDevices(),this._checkPluckers()}async _checkPluckers(){if(this._api){try{const{vendors:e}=await this._api.listPluckVendors();this._pluckersAvailable=e.length>0}catch{this._pluckersAvailable=!1}"plucker"!==this._activeTab||this._pluckersAvailable||this._switchTab("devices")}}_tagline(){return ke(`panel.tagline.${this._activeTab}`)}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=ke("panel.load_failed",{message:e.message})}finally{this._loading=!1}}}_toggleDevice(e){this._expandedDeviceId=this._expandedDeviceId===e?null:e}_openAddDialog(){this._addDialogOpen=!0}_onNavigatePlucker(e){this._pendingPluckEntity=e.detail?.vendor_entity_id??"",this._switchTab("plucker")}_onNavigateDevice(e){this._switchTab("devices"),this._expandedDeviceId=e.detail}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._expandedDeviceId=e.detail.id}async _onDeviceChanged(){await this._refreshDevices()}async _onDeviceDeleted(){this._expandedDeviceId=null,await this._refreshDevices()}_switchTab(e){this._expandedDeviceId=null,this._activeTab=e,"devices"===e&&this._refreshDevices()}_openHaSidebar(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}render(){return this._api?B`
            <ha-top-app-bar-fixed>
                <ha-menu-button
                    slot="navigationIcon"
                    .hass=${this.hass}
                ></ha-menu-button>

            <div class="mobile-nav-row">
                <button
                    class="mobile-nav-button"
                    title=${ke("panel.open_menu")}
                    aria-label=${ke("panel.open_menu")}
                    @click=${this._openHaSidebar}
                >
                    <ha-svg-icon
                        .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                    ></ha-svg-icon>
                </button>
            </div>

            <div class="header-banner">
                <img
                    src="/hair_panel/assets/hair-header.png"
                    alt="HAIR"
                    class="header-img"
                />
            </div>

            <div class="tab-bar">
                <button
                    class="tab ${"devices"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("devices")}
                >
                    ${ke("panel.tab.devices")}
                </button>
                <button
                    class="tab ${"sniffer"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
                <button
                    class="tab ${"clips"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("clips")}
                >
                    Clipper
                </button>
                ${this._pluckersAvailable?B`<button
                          class="tab ${"plucker"===this._activeTab?"active":""}"
                          @click=${()=>this._switchTab("plucker")}
                      >
                          Plucker
                      </button>`:""}
                <button
                    class="tab mirror-tab ${"mirror"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("mirror")}
                >
                    Mirror
                </button>
            </div>

            <div class="tab-tagline">${this._tagline()}</div>

            <div class="content">
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}
                ${"devices"===this._activeTab?B`
                          <ir-device-list
                              .devices=${this._devices}
                              .hass=${this.hass}
                              .api=${this._api}
                              .loading=${this._loading}
                              .expandedDeviceId=${this._expandedDeviceId}
                              @device-selected=${e=>this._toggleDevice(e.detail)}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                              @navigate-sniffer=${()=>this._switchTab("sniffer")}
                              @navigate-clips=${()=>this._switchTab("clips")}
                              @navigate-mirror=${()=>this._switchTab("mirror")}
                              @navigate-plucker=${this._onNavigatePlucker}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                      `:"sniffer"===this._activeTab?B`
                            <ir-signal-monitor
                                .api=${this._api}
                                .hass=${this.hass}
                                @navigate-device=${this._onNavigateDevice}
                            ></ir-signal-monitor>
                        `:"clips"===this._activeTab?B`
                              <ir-clips
                                  .api=${this._api}
                                  .hass=${this.hass}
                                  @navigate-device=${this._onNavigateDevice}
                              ></ir-clips>
                          `:"plucker"===this._activeTab?B`
                                <ir-pluck
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    .pendingEntity=${this._pendingPluckEntity}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-pluck>
                            `:B`
                                <ir-mirror
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-mirror>
                            `}
            </div>

            ${this._addDialogOpen?B`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `:""}

            <div class="version-footer">v${"0.6.7"}</div>
            </ha-top-app-bar-fixed>
        `:B`<div class="loading">${ke("panel.loading")}</div>`}};Ha.styles=n`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
        }
        .version-footer {
            text-align: center;
            color: var(--secondary-text-color);
            opacity: 0.5;
            font-size: 12px;
            padding: 24px 0 16px;
        }
        .header-banner {
            max-width: 1100px;
            margin: 0 auto;
            padding: 12px 16px 0;
            text-align: center;
        }
        .header-img {
            max-width: 100%;
            height: auto;
            max-height: 120px;
            object-fit: contain;
            border-radius: 6px;
        }
        .tab-tagline {
            max-width: 1100px;
            margin: 0 auto;
            padding: 8px 16px 0;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .tab-bar {
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--divider-color);
            padding: 0 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .tab-spacer {
            flex: 1;
        }
        .add-device-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            background: none;
            color: var(--primary-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            cursor: pointer;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .add-device-btn:hover {
            background: var(--secondary-background-color);
        }
        /* Clipper's tab-bar create button: identical to Add Device (gray
           stroke, neutral hover), just with copper text + icon. */
        .clipper-create-btn {
            color: #b87333;
        }
        .add-device-btn ha-svg-icon {
            --mdc-icon-size: 14px;
        }
        .tab {
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 20px;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            transition: color 150ms ease, border-color 150ms ease;
            font-family: inherit;
        }
        .tab:hover {
            color: var(--primary-text-color);
        }
        .tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }
        /* The Mirror wears silver (v0.6.6), matching its tab accent. */
        .tab.mirror-tab.active {
            color: #607d8b;
            border-bottom-color: #607d8b;
        }
        .content {
            padding: 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .loading {
            padding: 48px;
            text-align: center;
            color: var(--secondary-text-color);
        }

        /* Mobile-only navigation row.
           Custom HA panels can have their system header hidden by the
           parent shell on the HA Companion app, especially on iOS where
           swipe-to-go-back does not exist as a platform gesture. Adding
           a hamburger inside the panel content guarantees mobile users
           always have a visible nav target. Hidden on desktop because
           the ha-top-app-bar-fixed above already exposes the same menu
           button there, and a second control would be redundant. */
        .mobile-nav-row {
            display: none;
        }
        @media (max-width: 768px) {
            .mobile-nav-row {
                display: flex;
                align-items: center;
                padding: 8px 12px 0;
                max-width: 1100px;
                margin: 0 auto;
            }
        }
        .mobile-nav-button {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            color: var(--secondary-text-color);
            padding: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 150ms ease, color 150ms ease;
        }
        .mobile-nav-button:hover {
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
        }
        .mobile-nav-button ha-svg-icon {
            --mdc-icon-size: 22px;
        }
    `,e([pe({attribute:!1})],Ha.prototype,"hass",void 0),e([pe({attribute:!1})],Ha.prototype,"narrow",void 0),e([pe({attribute:!1})],Ha.prototype,"route",void 0),e([pe({attribute:!1})],Ha.prototype,"panel",void 0),e([ge()],Ha.prototype,"_activeTab",void 0),e([ge()],Ha.prototype,"_devices",void 0),e([ge()],Ha.prototype,"_expandedDeviceId",void 0),e([ge()],Ha.prototype,"_loading",void 0),e([ge()],Ha.prototype,"_error",void 0),e([ge()],Ha.prototype,"_addDialogOpen",void 0),e([ge()],Ha.prototype,"_pluckersAvailable",void 0),e([ge()],Ha.prototype,"_pendingPluckEntity",void 0),Ha=e([ue("ha-panel-ir-devices")],Ha);export{Ha as HaPanelIrDevices};
