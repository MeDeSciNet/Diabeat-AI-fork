package rl.collab.diabeat

import android.content.Context
import android.os.Bundle
import android.view.KeyEvent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import rl.collab.diabeat.databinding.ActivityMainBinding
import rl.collab.diabeat.frag.MyViewModel

class MainActivity : AppCompatActivity() {
    private val vm by viewModels<MyViewModel>()

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_UP) {
            vm.setHost(this)
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val binding = ActivityMainBinding.inflate(layoutInflater)
        binding.apply {
            setContentView(root)
            ViewCompat.setOnApplyWindowInsetsListener(main) { v, insets ->
                val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
                v.updatePadding(systemBars.left, systemBars.top, systemBars.right)
                insets
            }
            val navHostFragment = supportFragmentManager.findFragmentById(R.id.container) as NavHostFragment
            navView.setupWithNavController(navHostFragment.navController)
        }

        val masterKey = MasterKey.Builder(applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        vm.remePref = EncryptedSharedPreferences.create(
            applicationContext,
            "reme",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )

        vm.hostPref = getSharedPreferences("host", Context.MODE_PRIVATE)
        if (vm.hostStartup)
            vm.setHost(this)
        else
            vm.resetRetro(vm.hostAddr)
    }
}