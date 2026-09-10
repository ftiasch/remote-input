/*
 * remoteinput — fcitx5 addon that commits a UTF-8 string into the current input
 * context.
 *
 * Why an addon: fcitx5 has no D-Bus API to commit text. Controller1 only carries
 * activate/deactivate/switch-input-method style calls, and commitString() is only
 * reachable from inside the fcitx5 process. This addon is that one seam.
 *
 * It exports on the session bus:
 *   service   org.fcitx.Fcitx5       (reuses the connection of the dbus module)
 *   path      /remoteinput
 *   interface org.fcitx.Fcitx.RemoteInput1
 *   method    bool Commit(s text)
 */
#include <fcitx-utils/dbus/bus.h>
#include <fcitx-utils/dbus/objectvtable.h>
#include <fcitx-utils/log.h>
#include <fcitx/addonfactory.h>
#include <fcitx/addoninstance.h>
#include <fcitx/addonmanager.h>
#include <fcitx/inputcontext.h>
#include <fcitx/instance.h>

#include <string>

#include <dbus_public.h>

namespace {

constexpr char kObjectPath[] = "/remoteinput";
constexpr char kInterface[] = "org.fcitx.Fcitx.RemoteInput1";

class RemoteInput : public fcitx::AddonInstance,
                    public fcitx::dbus::ObjectVTable<RemoteInput> {
public:
    explicit RemoteInput(fcitx::Instance *instance) : instance_(instance) {
        auto *module = instance_->addonManager().addon("dbus", true);
        auto *bus = module ? module->call<fcitx::IDBusModule::bus>() : nullptr;
        if (!bus || !bus->addObjectVTable(kObjectPath, kInterface, *this)) {
            FCITX_ERROR() << "remoteinput: cannot export " << kInterface;
            return;
        }
        FCITX_INFO() << "remoteinput: exported " << kInterface << " at "
                     << kObjectPath;
    }

    /// Commit(text) -> whether an input context accepted the text.
    FCITX_OBJECT_VTABLE_METHOD(commit, "Commit", "s", "b");

    bool commit(const std::string &text) {
        auto *ic = instance_->mostRecentInputContext();
        if (!ic) {
            FCITX_WARN() << "remoteinput: no input context to commit into";
            return false;
        }
        ic->commitString(text);
        return true;
    }

private:
    fcitx::Instance *instance_;
};

class RemoteInputFactory : public fcitx::AddonFactory {
public:
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        return new RemoteInput(manager->instance());
    }
};

} // namespace

FCITX_ADDON_FACTORY_V2(remoteinput, RemoteInputFactory)
