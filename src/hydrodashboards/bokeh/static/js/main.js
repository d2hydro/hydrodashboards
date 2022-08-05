createAnimationUtils =  () => {

    elementsTagged = false;
    menuAnimation = 600;
    animationTag = "menu-animation-tag";
    animationWidthClass = "menu-animation-width";
    animationToolbarClass = "menu-animation-toolbar";
    animationSliderClass = "menu-animation-slider";
    activeClass = "animation-active";
    components = ["kaart","map_opt","but_leg", "grafiek", "grafiek-slider", "grafiek-lower"];

    addSliderTags = () => {
        const sliderElement = this.getSliderElement();
        sliderElement.addClass(this.animationSliderClass);
        sliderElement.addClass(this.animationTag);
    };
    
    addToolbarTags = (rootElementId) => {
        const toolbar = this.getRootElement(rootElementId).find('div.bk.bk-toolbar.bk-above').parent();
        toolbar.addClass(this.animationToolbarClass);
        toolbar.addClass(this.animationTag);
    };
    
    addContainerTags = (rootElementId, maxDepth) => {
        const rootElement = this.getRootElement(rootElementId);
        if (rootElement.length > 0) {
            let keepGoing = true;
            let currentElement = $(rootElement[0]);
            let currentDepth = 0;
            while (keepGoing) {
                
                currentDepth++;
                currentElement = this.getChildBokehElementWithFixedWidth(currentElement);
                if (currentElement) {
                    currentElement.addClass(this.animationWidthClass);
                    currentElement.addClass(this.animationTag);
                } 
                if (!currentElement || maxDepth <= currentDepth) {
                    keepGoing = false;
                }
            }
        }
    };

    addActiveClass = () => {
        $("." + this.animationTag).addClass(this.activeClass);
    };

    removeActiveClass = () => {
        $("." + this.animationTag).removeClass(this.activeClass);
    };
    
    getRootElement = (rootElementId) => {
        return $('#' + rootElementId).find('div.bk-root');
    };
    
    getSliderElement = () => {
        return this.getRootElement("grafiek-slider").children().children();
    };
    
    getChildBokehElementWithFixedWidth = (parent) => {
        if (parent && parent.length > 0) {
            const element = parent.children('div.bk').filter(function() {
                let widthEl = this.style && this.style.width;
                return widthEl !== undefined && widthEl !== null && widthEl !== "0px" && widthEl.indexOf("px") !== -1;
            });
            if (element && element.length > 0) {
                return element;
            }
        }
        return null;
    };

    dispatchResizeEvent = () => {
        window.dispatchEvent(new Event('resize'));
    };
    
    return {

        dispatchResizeEvent: () => {
            this.dispatchResizeEvent();
        },
    
        tagElements: () => {
            if (!this.elementsTagged) {
                for (let i = 0; i < this.components.length; i++) {
                    this.addContainerTags(this.components[i], 3);
                }
                this.addSliderTags();
                this.addToolbarTags("kaart");
                this.addToolbarTags("grafiek");
                this.elementsTagged = true;
            }
        },
    
        onResizePage: () => {
            this.addActiveClass();
    
            setTimeout((() => {
                this.dispatchResizeEvent();
                this.removeActiveClass();
            }).bind(this), this.menuAnimation);
        }

    }
}

window.AnimationUtils = createAnimationUtils();
