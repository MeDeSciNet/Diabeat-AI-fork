package rl.collab.diabeat.frag

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.viewbinding.ViewBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Response
import rl.collab.diabeat.Api
import rl.collab.diabeat.Request
import rl.collab.diabeat.Result
import rl.collab.diabeat.dialog
import rl.collab.diabeat.neu
import rl.collab.diabeat.pos
import rl.collab.diabeat.syncEdit
import rl.collab.diabeat.toast
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.util.concurrent.CancellationException

abstract class MyFrag<V : ViewBinding>(private val binder: (LayoutInflater, ViewGroup?, Boolean) -> V) : Fragment() {
    private var _binding: V? = null
    protected val binding get() = _binding!!

    protected val con get() = requireContext()
    protected val resolver get() = con.contentResolver!!
    private val act get() = requireActivity()
    protected val vm by activityViewModels<MyViewModel>()
    protected val viewLifecycleScope get() = viewLifecycleOwner.lifecycleScope
    protected fun launch(block: suspend CoroutineScope.() -> Unit) =
        viewLifecycleScope.launch(block = block)

    private suspend fun io(block: suspend CoroutineScope.() -> Unit) =
        withContext(Dispatchers.IO) { block() }

    protected abstract fun V.setView()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = binder(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.setView()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    protected fun <T> rq(binder: (LayoutInflater) -> T, req: T.() -> Unit) =
        binder(layoutInflater).apply(req)

    protected fun toast(msg: String) = con.toast(msg)

    protected fun dialog(
        title: String,
        msg: String? = null,
        view: View? = null,
        pos: String? = "OK",
        neg: String? = "取消",
        neutral: String? = null,
        cancelable: Boolean = false
    ) = con.dialog(title, msg, view, pos, neg, neutral, cancelable)

    protected fun errDialog(msg: String, neutral: String? = null) =
        dialog("錯誤", msg, neg = null, neutral = neutral)

    protected fun exceptionDialog(e: Exception) {
        val z = e::class.java
        errDialog("${z.`package`?.name}\n${z.simpleName}\n\n${e.localizedMessage}")
    }

    protected fun refresh(refresh: String?, addOnSucceed: ((Result.Refresh) -> Unit)?, onFail: (() -> Unit)?) {
        val onSucceed = { r: Result.Refresh ->
            vm.access = "Bearer ${r.access}"
            addOnSucceed?.invoke(r)
            Unit
        }

        request(onSucceed, null, onFail, false) {
            val obj = Request.Refresh(refresh ?: vm.refresh!!)
            refresh(obj)
        }
    }

    protected fun <T> request(
        onSucceed: (T) -> Unit,
        onBadRequest: ((String?) -> String)?,
        onFail: (() -> Unit)?,
        isLong: Boolean,
        retroFun: suspend Api.() -> Response<T>
    ) =
        launch {
            try {
                var r: Response<T>? = null
                var status = 0

                io {
                    for (i in 0..1) {
                        r = (if (isLong) vm.retroLong else vm.retro).value.retroFun()
                        status = r!!.code()
                        if (status == 401)
                            refresh(null, null, null)
                        else
                            break
                    }
                }

                when (status) {
                    200, 201 -> onSucceed(r!!.body()!!)
                    400 -> {
                        val str = r!!.errorBody()?.string()
                        errDialog(onBadRequest?.invoke(str) ?: "請求錯誤")
                    }

                    401 -> {
                        vm.remePref.syncEdit { clear() }
                        errDialog("無密碼登入憑證過期，請重新登入").pos.setOnClickListener {
                            act.finishAffinity()
                        }
                    }

                    else -> errDialog("HTTP $status")
                }

                if (status != 200 && status != 201)
                    onFail?.invoke()

            } catch (e: Exception) {
                fun setHostErrDialog(msg: String) {
                    val dialog = errDialog(msg, "設定 Host")
                    dialog.neu.setOnClickListener {
                        dialog.dismiss()
                        vm.setHost(act)
                    }
                }

                when (e) {
                    is CancellationException -> {}
                    is ConnectException -> setHostErrDialog("無法連線到${vm.addr}")
                    is SocketTimeoutException -> setHostErrDialog("連線逾時")
                    else -> exceptionDialog(e)
                }
                onFail?.invoke()
            }
        }
}